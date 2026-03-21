#!/usr/bin/env python3
"""
Bolt AI — Backup System Module
Creates local backups of all data to prevent data loss.
"""

import json
import shutil
import logging
import hashlib
import gzip
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("bolt.backup")


class BackupSystem:
    """Manage local backups of Bolt AI data."""
    
    def __init__(self, base_path: str = None):
        import os
        if base_path is None:
            base_path = os.environ.get(
                "BOLT_BASE_PATH",
                str(Path(__file__).parent.parent)
            )
        self.base_path = Path(base_path)
        self.backup_dir = self.base_path / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Data directories to backup
        self.data_dirs = [
            "data/queue",
            "data/published", 
            "data/analytics",
            "content/audio",
            "content/video",
            "content/thumbnails",
            "logs"
        ]
        
        # Config files to backup
        self.config_files = [
            "code/config.json"
        ]
        
        # Max backups to keep
        self.max_daily_backups = 7    # Keep 7 daily
        self.max_weekly_backups = 4   # Keep 4 weekly
        self.max_monthly_backups = 12  # Keep 12 monthly
        
    def create_backup(self, backup_type: str = "manual") -> Dict:
        """
        Create a backup of all data.
        
        Args:
            backup_type: Type of backup (manual, daily, weekly, monthly)
            
        Returns:
            Backup info dict with path and checksum
        """
        timestamp = datetime.now(timezone.utc)
        date_str = timestamp.strftime("%Y%m%d")
        time_str = timestamp.strftime("%H%M%S")
        
        # Create backup filename
        backup_name = f"bolt_backup_{backup_type}_{date_str}_{time_str}"
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(exist_ok=True)
        
        total_size = 0
        files_backed_up = []
        
        # Backup data directories
        for data_dir in self.data_dirs:
            source = self.base_path / data_dir
            if source.exists():
                dest = backup_path / data_dir
                dest.parent.mkdir(parents=True, exist_ok=True)
                
                if source.is_dir():
                    # Copy directory
                    shutil.copytree(source, dest, dirs_exist_ok=True)
                    file_count = sum(1 for _ in dest.rglob("*") if _.is_file())
                else:
                    # Single file
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, dest)
                    file_count = 1
                
                dir_size = sum(f.stat().st_size for f in dest.rglob("*") if f.is_file())
                total_size += dir_size
                
                files_backed_up.append({
                    "path": str(data_dir),
                    "files": file_count,
                    "size_bytes": dir_size
                })
                
                logger.info(f"  ✅ Backed up {data_dir}: {file_count} files")
        
        # Backup config files
        for config_file in self.config_files:
            source = self.base_path / config_file
            if source.exists():
                dest = backup_path / config_file
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest)
                files_backed_up.append({
                    "path": str(config_file),
                    "files": 1,
                    "size_bytes": source.stat().st_size
                })
                total_size += source.stat().st_size
        
        # Create backup manifest
        manifest = {
            "backup_id": backup_name,
            "timestamp": timestamp.isoformat(),
            "backup_type": backup_type,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "files": files_backed_up,
            "version": "2.0"
        }
        
        # Save manifest
        with open(backup_path / "manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # Create checksum file
        checksum = self._create_checksum(backup_path)
        with open(backup_path / "checksum.sha256", 'w') as f:
            f.write(checksum)
        
        # Compress backup
        compressed_path = self._compress_backup(backup_path)
        
        # Clean up uncompressed if compression successful
        if compressed_path:
            shutil.rmtree(backup_path)
        
        # Auto-cleanup old backups
        self._cleanup_old_backups()
        
        backup_info = {
            "backup_id": backup_name,
            "timestamp": timestamp.isoformat(),
            "type": backup_type,
            "size_mb": manifest["total_size_mb"],
            "files_count": sum(f["files"] for f in files_backed_up),
            "compressed": compressed_path is not None,
            "path": str(compressed_path or backup_path),
            "checksum": checksum
        }
        
        logger.info(f"✅ Backup complete: {backup_name} ({manifest['total_size_mb']} MB)")
        
        return backup_info
    
    def _create_checksum(self, backup_path: Path) -> str:
        """Create SHA256 checksum of entire backup."""
        hasher = hashlib.sha256()
        
        for item in sorted(backup_path.rglob("*")):
            if item.is_file():
                hasher.update(item.name.encode())
                hasher.update(str(item.stat().st_size).encode())
        
        return hasher.hexdigest()
    
    def _compress_backup(self, backup_path: Path) -> Optional[Path]:
        """Compress backup to .tar.gz"""
        try:
            import tarfile
            
            archive_name = f"{backup_path}.tar.gz"
            
            with tarfile.open(archive_name, "w:gz") as tar:
                tar.add(backup_path, arcname=backup_path.name)
            
            # Get compressed size
            compressed_size = Path(archive_name).stat().st_size
            
            logger.info(f"  📦 Compressed: {archive_name} ({compressed_size / 1024 / 1024:.2f} MB)")
            
            return Path(archive_name)
            
        except Exception as e:
            logger.warning(f"Compression failed: {e}")
            return None
    
    def _cleanup_old_backups(self) -> None:
        """Remove old backups based on retention policy."""
        # Get all backups sorted by date
        backups = sorted(self.backup_dir.glob("bolt_backup_*"), 
                        key=lambda x: x.stat().st_mtime, 
                        reverse=True)
        
        # Separate by type
        daily = [b for b in backups if "daily" in b.name]
        weekly = [b for b in backups if "weekly" in b.name]
        monthly = [b for b in backups if "monthly" in b.name]
        manual = [b for b in backups if "manual" in b.name]
        
        # Keep only the most recent of each type
        def cleanup(backups_list, max_keep):
            to_delete = backups_list[max_keep:]
            for backup in to_delete:
                try:
                    if backup.is_dir():
                        shutil.rmtree(backup)
                    else:
                        backup.unlink()
                    logger.info(f"  🗑️  Deleted old backup: {backup.name}")
                except Exception as e:
                    logger.warning(f"  Failed to delete {backup}: {e}")
        
        cleanup(daily, self.max_daily_backups)
        cleanup(weekly, self.max_weekly_backups)
        cleanup(monthly, self.max_monthly_backups)
        
        # Always keep at least 3 manual backups
        if len(manual) > 3:
            cleanup(manual, 3)
    
    def restore_backup(self, backup_id: str) -> bool:
        """
        Restore from a backup.
        
        Args:
            backup_id: The backup ID to restore
            
        Returns:
            True if successful
        """
        # Find backup
        backup_path = None
        for ext in ["", ".tar.gz"]:
            candidate = self.backup_dir / f"bolt_backup_{backup_id}{ext}"
            if candidate.exists():
                backup_path = candidate
                break
        
        if not backup_path:
            logger.error(f"Backup not found: {backup_id}")
            return False
        
        # Extract if compressed
        extract_to = self.backup_dir / f"bolt_backup_{backup_id}_temp"
        
        try:
            if str(backup_path).endswith(".tar.gz"):
                import tarfile
                with tarfile.open(backup_path, "r:gz") as tar:
                    tar.extractall(extract_to)
                backup_path = extract_to
        except Exception as e:
            logger.error(f"Failed to extract backup: {e}")
            return False
        
        # Restore files
        manifest = None
        try:
            with open(backup_path / "manifest.json") as f:
                manifest = json.load(f)
        except:
            pass
        
        # Copy files back
        for item in (backup_path).iterdir():
            if item.name == "manifest.json" or item.name == "checksum.sha256":
                continue
            
            dest = self.base_path / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)
        
        # Clean up temp
        if extract_to.exists():
            shutil.rmtree(extract_to)
        
        logger.info(f"✅ Restored from backup: {backup_id}")
        return True
    
    def list_backups(self) -> List[Dict]:
        """List all available backups."""
        backups = []
        
        for backup_path in sorted(self.backup_dir.glob("bolt_backup_*"), 
                                 key=lambda x: x.stat().st_mtime, 
                                 reverse=True):
            # Try to read manifest
            manifest_path = backup_path / "manifest.json"
            if manifest_path.exists():
                with open(manifest_path) as f:
                    manifest = json.load(f)
                    backups.append({
                        "id": manifest["backup_id"],
                        "timestamp": manifest["timestamp"],
                        "type": manifest["backup_type"],
                        "size_mb": manifest["total_size_mb"],
                        "files": sum(f["files"] for f in manifest["files"])
                    })
            else:
                # Compressed backup
                stat = backup_path.stat()
                backups.append({
                    "id": backup_path.name.replace("bolt_backup_", "").replace(".tar.gz", ""),
                    "timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "type": "unknown",
                    "size_mb": round(stat.st_size / 1024 / 1024, 2),
                    "files": "N/A"
                })
        
        return backups
    
    def get_backup_info(self, backup_id: str) -> Optional[Dict]:
        """Get detailed info about a specific backup."""
        backups = self.list_backups()
        for backup in backups:
            if backup["id"] == backup_id:
                return backup
        return None


# Convenience functions
def create_daily_backup():
    """Create a daily backup."""
    backup = BackupSystem()
    return backup.create_backup("daily")


def create_weekly_backup():
    """Create a weekly backup."""
    backup = BackupSystem()
    return backup.create_backup("weekly")


def create_monthly_backup():
    """Create a monthly backup."""
    backup = BackupSystem()
    return backup.create_backup("monthly")


def restore_latest_backup():
    """Restore the most recent backup."""
    backup = BackupSystem()
    backups = backup.list_backups()
    if backups:
        return backup.restore_backup(backups[0]["id"])
    return False


if __name__ == "__main__":
    # Test the backup system
    print("🗄️  Bolt AI Backup System Test")
    
    backup = BackupSystem()
    
    # Create a test backup
    print("\n📦 Creating test backup...")
    result = backup.create_backup("manual")
    print(f"  Created: {result}")
    
    # List backups
    print("\n📋 Available backups:")
    for b in backup.list_backups():
        print(f"  - {b['id']}: {b['size_mb']} MB ({b['type']})")
