#!/usr/bin/env python3
"""Bolt AI v2 -- Unified Entry Point

Single entry point for all Bolt operations, like Operator 1's main.py.
Routes to the appropriate subsystem based on the command.

Usage:
    python main.py pipeline                  # Full content pipeline
    python main.py pipeline --step news      # Single pipeline step
    python main.py pipeline --schedule       # 24/7 daemon mode

    python main.py server                    # Start FastAPI backend (port 8000)

    python main.py probe                     # Probe all RSS feeds
    python main.py probe --source "OpenAI Blog"  # Probe one source

    python main.py extract "Article title" "Summary text"  # Fuzzy classify
    python main.py extract --llm "Title" "Summary"         # LLM + fuzzy

    python main.py costs                     # Show cost summary
    python main.py backups                   # List backups
    python main.py backups --create manual   # Create backup
    python main.py db stats                  # Database statistics
    python main.py secrets                   # Audit configured secrets
"""

import argparse
import sys
from pathlib import Path

# Ensure code/ is on the path
sys.path.insert(0, str(Path(__file__).parent / "code"))


def cmd_pipeline(args):
    """Run the content pipeline (delegates to content_automation_master.py)."""
    from content_automation_master import main as pipeline_main
    # Re-inject args so content_automation_master sees them
    sys.argv = ["content_automation_master.py"]
    if args.step:
        sys.argv += ["--step", args.step]
    if args.schedule:
        sys.argv.append("--schedule")
    if args.config:
        sys.argv += ["--config", args.config]
    pipeline_main()


def cmd_server(args):
    """Start the FastAPI backend server."""
    import uvicorn
    uvicorn.run(
        "api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


def cmd_probe(args):
    """Probe RSS news sources."""
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if args.source:
        from news_source_prober import deep_probe_source, _print_probe_result
        from shared_config import get_config
        config = get_config()
        sources = config.get("news_sources", {})
        if args.source in sources:
            result = deep_probe_source(args.source, sources[args.source]["url"],
                                        sources[args.source].get("reliability", 0))
            print(f"\n{'='*65}")
            print(f"  Deep Probe: {args.source}")
            print(f"{'='*65}")
            _print_probe_result(result)
            print(f"{'='*65}\n")
        else:
            print(f"Source '{args.source}' not found. Available: {', '.join(sources.keys())}")
    elif args.quick:
        from news_aggregator import probe_feeds
        probe_feeds()
    else:
        from news_source_prober import deep_probe_all, _print_probe_result
        results = deep_probe_all()
        print(f"\n{'='*65}")
        print(f"  Deep Probe Results ({sum(1 for r in results if r.status=='ok')}/{len(results)} OK)")
        print(f"{'='*65}")
        for r in results:
            _print_probe_result(r)
        print(f"{'='*65}\n")


def cmd_extract(args):
    """Extract/classify article content."""
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    from content_extractor import extract_article

    config = None
    if args.llm:
        from shared_config import get_config
        config = get_config()

    result = extract_article(
        title=args.title,
        summary=args.summary or "",
        config=config,
        force_fuzzy=not args.llm,
    )

    print(f"\n{'='*55}")
    print(f"  Content Extraction ({result.source_method})")
    print(f"{'='*55}")
    print(f"  Title:      {result.title[:60]}")
    print(f"  Pillar:     {result.pillar}")
    print(f"  Category:   {result.category}")
    print(f"  Impact:     {result.impact_score:.1f}/10")
    print(f"  Sentiment:  {result.sentiment}")
    print(f"  Companies:  {', '.join(result.companies_mentioned) or 'none'}")
    print(f"  Tech:       {', '.join(result.technologies_mentioned) or 'none'}")
    print(f"  Relevance:  {result.audience_relevance:.1f}/10")
    if result.hook_idea:
        print(f"  Hook:       {result.hook_idea}")
    if result.key_facts:
        print(f"  Facts:")
        for f in result.key_facts[:3]:
            print(f"    - {f[:80]}")
    print(f"{'='*55}\n")


def cmd_costs(args):
    """Show cost summary."""
    from content_automation_master import CostTracker
    t = CostTracker()
    total = t.get_total_summary()
    m = t.get_monthly_summary()
    print(f"\n{'='*45}")
    print(f"  Bolt Cost Summary")
    print(f"{'='*45}")
    print(f"  Total:     ${total['total_spent']:.4f} across {total['total_videos']} videos")
    print(f"  Avg/video: ${total['avg_cost_per_video']:.4f}")
    print(f"  Month:     ${m['total_cost']:.4f} across {m['videos']} videos")
    for svc, cost in sorted(m.get("services", {}).items(), key=lambda x: x[1], reverse=True):
        print(f"    {svc:20s} ${cost:.4f}")
    print(f"{'='*45}\n")


def cmd_backups(args):
    """List or create backups."""
    from backup_system import BackupSystem
    bs = BackupSystem()
    if args.create:
        r = bs.create_backup(args.create)
        print(f"Backup created: {r['backup_id']} ({r['size_mb']} MB)")
    elif args.restore:
        ok = bs.restore_backup(args.restore)
        print(f"{'Restored' if ok else 'Failed'}: {args.restore}")
    else:
        backups = bs.list_backups()
        print(f"\n{'='*55}")
        print(f"  Bolt Backups")
        print(f"{'='*55}")
        for b in backups:
            print(f"  [{b['type']:8s}] {str(b['timestamp'])[:16]} {b['size_mb']:.1f} MB")
        print(f"{'='*55}\n")


def cmd_db(args):
    """Database operations."""
    from database import main as db_main
    sys.argv = ["database.py", args.subcmd or "stats"]
    db_main()


def cmd_secrets(args):
    """Audit configured secrets."""
    from secrets_manager import print_audit
    print_audit()


def main():
    parser = argparse.ArgumentParser(
        description="Bolt AI v2 -- Unified Entry Point",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # pipeline
    p_pipe = sub.add_parser("pipeline", help="Run the content pipeline")
    p_pipe.add_argument("--step", choices=["news", "script", "video", "publish", "analytics"])
    p_pipe.add_argument("--schedule", action="store_true", help="24/7 daemon mode")
    p_pipe.add_argument("--config", default="code/config.json")

    # server
    p_srv = sub.add_parser("server", help="Start FastAPI backend")
    p_srv.add_argument("--host", default="0.0.0.0")
    p_srv.add_argument("--port", type=int, default=8000)
    p_srv.add_argument("--reload", action="store_true", default=True)

    # probe
    p_probe = sub.add_parser("probe", help="Probe RSS news sources")
    p_probe.add_argument("--source", help="Probe a specific source by name")
    p_probe.add_argument("--quick", action="store_true", help="Quick probe (cached_get only)")

    # extract
    p_ext = sub.add_parser("extract", help="Extract/classify article content")
    p_ext.add_argument("title", help="Article title")
    p_ext.add_argument("summary", nargs="?", default="", help="Article summary/body")
    p_ext.add_argument("--llm", action="store_true", help="Use Claude LLM (requires API key)")

    # costs
    sub.add_parser("costs", help="Show cost summary")

    # backups
    p_bak = sub.add_parser("backups", help="Backup management")
    p_bak.add_argument("--create", choices=["daily", "weekly", "monthly", "manual"])
    p_bak.add_argument("--restore", metavar="BACKUP_ID")

    # db
    p_db = sub.add_parser("db", help="Database operations")
    p_db.add_argument("subcmd", nargs="?", choices=["stats", "costs", "scripts", "jobs"], default="stats")

    # secrets
    sub.add_parser("secrets", help="Audit configured secrets")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        "pipeline": cmd_pipeline,
        "server": cmd_server,
        "probe": cmd_probe,
        "extract": cmd_extract,
        "costs": cmd_costs,
        "backups": cmd_backups,
        "db": cmd_db,
        "secrets": cmd_secrets,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
