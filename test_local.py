"""
Local test runner for AI Code Review Automation.
Allows testing the review agents without GitHub integration.

Usage:
    python test_local.py path/to/file.py
    python test_local.py --all-agents path/to/file.py
    python test_local.py --agent security path/to/file.py
"""
import os
import sys
import asyncio
import argparse
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents import StyleAgent, SecurityAgent, PerformanceAgent, LogicAgent
from agents.base import IssueSeverity


def print_colored(text: str, color: str = "white"):
    """Print colored text to terminal."""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, '')}{text}{colors['reset']}")


def get_severity_color(severity: IssueSeverity) -> str:
    """Get color for severity level."""
    return {
        IssueSeverity.CRITICAL: "red",
        IssueSeverity.HIGH: "red",
        IssueSeverity.MEDIUM: "yellow",
        IssueSeverity.LOW: "blue",
        IssueSeverity.INFO: "cyan"
    }.get(severity, "white")


def get_severity_emoji(severity: IssueSeverity) -> str:
    """Get emoji for severity level."""
    return {
        IssueSeverity.CRITICAL: "🔴",
        IssueSeverity.HIGH: "🟠",
        IssueSeverity.MEDIUM: "🟡",
        IssueSeverity.LOW: "🔵",
        IssueSeverity.INFO: "⚪"
    }.get(severity, "⚪")


async def run_review(file_path: str, api_key: str, agents_to_run: list):
    """Run code review on a file."""
    
    # Read file
    try:
        with open(file_path, 'r') as f:
            code = f.read()
    except FileNotFoundError:
        print_colored(f"❌ File not found: {file_path}", "red")
        return
    except Exception as e:
        print_colored(f"❌ Error reading file: {e}", "red")
        return
    
    print_colored(f"\n📁 Reviewing: {file_path}", "cyan")
    print_colored(f"📏 Lines: {len(code.splitlines())}", "white")
    print_colored("-" * 60, "white")
    
    # Map agent names to classes
    agent_map = {
        "style": ("🎨 Style", StyleAgent),
        "security": ("🔒 Security", SecurityAgent),
        "performance": ("⚡ Performance", PerformanceAgent),
        "logic": ("🧠 Logic", LogicAgent)
    }
    
    all_issues = []
    
    for agent_name in agents_to_run:
        if agent_name not in agent_map:
            print_colored(f"⚠️ Unknown agent: {agent_name}", "yellow")
            continue
        
        title, AgentClass = agent_map[agent_name]
        print_colored(f"\n{title} Agent analyzing...", "magenta")
        
        try:
            agent = AgentClass(api_key)
            review = await agent.review_code(code, file_path)
            
            if review.issues:
                for issue in review.issues:
                    all_issues.append(issue)
                    emoji = get_severity_emoji(issue.severity)
                    color = get_severity_color(issue.severity)
                    
                    print_colored(f"\n{emoji} [{issue.severity.value.upper()}] {issue.title}", color)
                    print_colored(f"   Line {issue.line_start}", "white")
                    print_colored(f"   {issue.description}", "white")
                    if issue.suggestion:
                        print_colored(f"   💡 {issue.suggestion}", "green")
            else:
                print_colored(f"   ✅ No issues found", "green")
                
        except Exception as e:
            print_colored(f"   ❌ Error: {e}", "red")
    
    # Summary
    print_colored("\n" + "=" * 60, "white")
    print_colored("📊 SUMMARY", "cyan")
    print_colored("=" * 60, "white")
    
    if all_issues:
        by_severity = {}
        for issue in all_issues:
            by_severity[issue.severity.value] = by_severity.get(issue.severity.value, 0) + 1
        
        print_colored(f"Total issues: {len(all_issues)}", "white")
        for sev, count in sorted(by_severity.items()):
            print_colored(f"  {sev}: {count}", "white")
    else:
        print_colored("✅ No issues found! Your code looks good.", "green")


def main():
    parser = argparse.ArgumentParser(
        description="Local test runner for AI Code Review"
    )
    parser.add_argument(
        "file",
        help="Path to the file to review"
    )
    parser.add_argument(
        "--agent", "-a",
        choices=["style", "security", "performance", "logic"],
        help="Run only a specific agent"
    )
    parser.add_argument(
        "--all-agents",
        action="store_true",
        default=True,
        help="Run all agents (default)"
    )
    parser.add_argument(
        "--api-key",
        help="Optional: specific Gemini API key to use"
    )
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Get API key - now optional since we have multi-provider support
    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
    
    # Check if any provider is available
    if not api_key:
        # Check for multi-provider keys
        has_gemini_keys = bool(os.environ.get("GEMINI_API_KEYS"))
        has_groq_key = bool(os.environ.get("GROQ_API_KEY"))
        
        if not has_gemini_keys and not has_groq_key:
            print_colored("❌ No API keys configured!", "red")
            print_colored("Set one of these in your .env file:", "yellow")
            print_colored("  GEMINI_API_KEY=your_key", "white")
            print_colored("  GEMINI_API_KEYS=key1,key2", "white")
            print_colored("  GROQ_API_KEY=your_groq_key", "white")
            sys.exit(1)
    
    # Determine which agents to run
    if args.agent:
        agents_to_run = [args.agent]
    else:
        agents_to_run = ["style", "security", "performance", "logic"]
    
    print_colored("\n🤖 AI Code Review - Local Test", "cyan")
    print_colored(f"Agents: {', '.join(agents_to_run)}", "white")
    
    # Run async review (api_key can be None for multi-provider mode)
    asyncio.run(run_review(args.file, api_key, agents_to_run))


if __name__ == "__main__":
    main()

