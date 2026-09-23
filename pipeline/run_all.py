"""Run the full Memory Lane pipeline in one command.

Usage:
    python -m pipeline.run_all           # Run all stages
    python -m pipeline.run_all --dry-run # Show what would run without executing
    python -m pipeline.run_all --skip-ingest --skip-transcripts  # Skip stages
"""

import argparse
import logging
import sys
import time

logging.basicConfig(
    force=True,  # beat pipeline.config's INFO default whatever imported first
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def print_header(text: str):
    width = 50
    print(f"\n{'=' * width}")
    print(f"  {text}")
    print(f"{'=' * width}\n")


def print_summary(results: dict):
    print_header("PIPELINE SUMMARY")

    total_time = results.get("total_time", 0)

    if "ingest" in results:
        r = results["ingest"]
        print(f"  Ingest:      {r.get('inserted', 0)} new, {r.get('skipped', 0)} existing")

    if "transcripts" in results:
        r = results["transcripts"]
        status = f"{r.get('fetched', 0)} fetched, {r.get('failed', 0)} failed"
        # Not results["error"]: extraction never touches YouTube and should
        # still run on what was fetched before the block.
        if r.get("error") == "blocked":
            status += " (stopped: YouTube is blocking this IP - set TRANSCRIPT_PROXY)"
        print(f"  Transcripts: {status}")

    if "extract" in results:
        r = results["extract"]
        status = f"{r.get('extracted', 0)} processed, {r.get('failed', 0)} failed"
        if r.get("error") == "billing":
            status += " (stopped: billing error)"
        print(f"  Extract:     {status}")

    print(f"\n  Total time:  {total_time:.1f}s")

    if results.get("error"):
        print(f"\n  Error: {results['error']}")
        return False

    print("\n  Pipeline complete!")
    return True


def run_pipeline(skip_ingest=False, skip_transcripts=False, skip_extract=False, dry_run=False):
    results = {}
    start_time = time.time()

    if not skip_ingest:
        print_header("STAGE 1: INGEST")
        if dry_run:
            print("  [DRY RUN] Would run: python -m pipeline.ingest")
            results["ingest"] = {"inserted": 0, "skipped": 0, "dry_run": True}
        else:
            try:
                from pipeline.ingest import ingest_content

                results["ingest"] = ingest_content()
            except Exception as e:
                logger.error(f"Ingest failed: {e}")
                results["ingest"] = {"error": str(e)}
                results["error"] = f"Ingest failed: {e}"
    else:
        print_header("STAGE 1: INGEST (skipped)")

    if not skip_transcripts and not results.get("error"):
        print_header("STAGE 2: TRANSCRIPTS")
        if dry_run:
            print("  [DRY RUN] Would run: python -m pipeline.transcripts")
            results["transcripts"] = {"fetched": 0, "failed": 0, "dry_run": True}
        else:
            try:
                from pipeline.transcripts import fetch_pending_transcripts

                results["transcripts"] = fetch_pending_transcripts()
            except Exception as e:
                logger.error(f"Transcript fetch failed: {e}")
                results["transcripts"] = {"error": str(e)}
                results["error"] = f"Transcripts failed: {e}"
    elif skip_transcripts:
        print_header("STAGE 2: TRANSCRIPTS (skipped)")

    if not skip_extract and not results.get("error"):
        print_header("STAGE 3: EXTRACT")
        if dry_run:
            print("  [DRY RUN] Would run: python -m pipeline.extract")
            results["extract"] = {"extracted": 0, "failed": 0, "dry_run": True}
        else:
            try:
                from pipeline.extract import extract_all_pending

                result = extract_all_pending()
                results["extract"] = result
                if result.get("error") == "billing":
                    results["error"] = "Extraction stopped due to billing error"
            except Exception as e:
                logger.error(f"Extraction failed: {e}")
                results["extract"] = {"error": str(e)}
                results["error"] = f"Extraction failed: {e}"
    elif skip_extract:
        print_header("STAGE 3: EXTRACT (skipped)")

    results["total_time"] = time.time() - start_time
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Run the full Memory Lane pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m pipeline.run_all                    # Run all stages
  python -m pipeline.run_all --dry-run          # Preview without running
  python -m pipeline.run_all --skip-ingest      # Skip ingest, run transcripts + extract
  python -m pipeline.run_all --extract-only     # Only run extraction
        """,
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would run without executing"
    )
    parser.add_argument("--skip-ingest", action="store_true", help="Skip the ingest stage")
    parser.add_argument(
        "--skip-transcripts", action="store_true", help="Skip the transcripts stage"
    )
    parser.add_argument("--skip-extract", action="store_true", help="Skip the extraction stage")
    parser.add_argument(
        "--extract-only",
        action="store_true",
        help="Only run extraction (skip ingest and transcripts)",
    )

    args = parser.parse_args()

    if args.extract_only:
        args.skip_ingest = True
        args.skip_transcripts = True

    print_header("MEMORY LANE PIPELINE")
    if args.dry_run:
        print("  Mode: DRY RUN (no changes will be made)\n")

    results = run_pipeline(
        skip_ingest=args.skip_ingest,
        skip_transcripts=args.skip_transcripts,
        skip_extract=args.skip_extract,
        dry_run=args.dry_run,
    )

    success = print_summary(results)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
