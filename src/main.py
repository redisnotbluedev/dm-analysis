import discord, dotenv, rich, os, rich.progress, datetime, discord.http, asyncio, json
from discord.ext import commands
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.console import Group

dotenv.load_dotenv()
bot = commands.Bot(command_prefix="!")
has_run = False
dms = []
console = Console()

def format_seconds(seconds):
	days = int(seconds // 86400)
	hours = int((seconds % 86400) // 3600)
	if days > 0:
		return f"{days}d {hours}h"
	return f"{hours}h"

def generate_leaderboard_table(title, data, key_fn, format_val_fn, header_name, reverse=True, limit=5, style="cyan"):
	"""Generates a Rich Table object using purely cached attributes."""
	sorted_data = sorted(data, key=key_fn, reverse=reverse)

	table = Table(title=f"[bold {style}]{title}[/]", title_justify="left", expand=True, border_style=style)
	table.add_column("Rank", justify="center", width=4)
	table.add_column("User", justify="left")
	table.add_column(header_name, justify="right")

	for idx, dm in enumerate(sorted_data[:limit]):
		table.add_row(
			f"#{idx + 1}",
			f"[bold]{dm['display_name']}[/] (@{dm['name']})",
			format_val_fn(dm)
		)
	return table

@bot.event
async def on_ready():
	global dms, has_run
	console.print(f"[bold green]Logged in as:[/] {bot.user.name} (ID: {bot.user.id})")

	if not has_run:
		has_run = True

		if os.path.exists("data.json"):
			console.print("[bold yellow]Found existing data.json. Loading local cache...[/]")
			with open("data.json", "r") as f:
				dms = json.load(f)
		else:
			console.print("[bold red]No local cache found. Analysing DM channels...[/]")
			for channel in rich.progress.track(bot.private_channels, "Analysing..."):
				if isinstance(channel, discord.DMChannel):
					search_route = discord.http.Route("GET", "/channels/{channel_id}/messages/search", channel_id=channel.id)

					try:
						data = await bot.http.request(search_route, params={"limit": 1})
						messages = data.get("total_results", 0)
					except Exception as e:
						messages = 0
						print(f"Failed to query search index: {e}")

					age = datetime.datetime.now(datetime.timezone.utc) - channel.created_at
					total_seconds = age.total_seconds()
					hours = total_seconds / 3600
					rate = messages / hours if hours > 0 else 0

					dms.append({
						"name": channel.recipient.name,
						"display_name": channel.recipient.display_name,
						"messages": messages,
						"age_seconds": total_seconds,
						"rate": rate
					})

					await asyncio.sleep(5)

			with open("data.json", "w") as f:
				json.dump(dms, f, indent=4)

		# --- RICH TEXT METRICS DISPLAY (USING EXCLUSIVELY CACHED DATA) ---

		# 1. Overall Aggregates Panel
		total_dms = len(dms)
		total_messages_across_all = sum(dm["messages"] for dm in dms)
		avg_messages = total_messages_across_all / total_dms if total_dms > 0 else 0

		stats_summary = Group(
			f"[bold]Total DM Channels Tracked:[/] [cyan]{total_dms}[/]",
			f"[bold]Combined Total Messages:[/]  [green]{total_messages_across_all:,}[/]",
			f"[bold]Average Messages per DM:[/]  [magenta]{avg_messages:.1f}[/]"
		)

		console.print("\n")
		console.print(Panel(stats_summary, title="[bold reverse white] 📊 OVERALL DM STATS [/]", expand=False, border_style="white"))
		console.print("\n")

		# 2. Side-by-Side Leaderboard Layouts
		# Row 1: Activity Leaderboards
		t1 = generate_leaderboard_table(
			title="🏆 MOST ACTIVE",
			data=dms,
			key_fn=lambda x: x["messages"],
			format_val_fn=lambda x: f"[green]{x['messages']:,}[/] msgs",
			header_name="Total Vol",
			style="spring_green3"
		)

		t2 = generate_leaderboard_table(
			title="⚡ HIGHEST RATE",
			data=dms,
			key_fn=lambda x: x["rate"],
			format_val_fn=lambda x: f"[cyan]{x['rate']:.4f}[/] /hr",
			header_name="Msgs/Hour",
			style="deep_sky_blue3"
		)

		console.print(Columns([t1, t2], expand=True))
		console.print("\n")

		# Row 2: Age Leaderboards
		t3 = generate_leaderboard_table(
			title="⏳ OLDEST DM CHANNELS",
			data=dms,
			key_fn=lambda x: x["age_seconds"],
			format_val_fn=lambda x: f"[yellow]{format_seconds(x['age_seconds'])}[/]",
			header_name="Age",
			style="gold3"
		)

		# Filter criteria relies purely on properties already cached inside data.json
		aged_dms = [dm for dm in dms if dm["age_seconds"] > 604800] # Over 7 days old
		t4 = generate_leaderboard_table(
			title="💀 GHOST TOWNS (Chats over 1 week old)",
			data=aged_dms,
			key_fn=lambda x: x["rate"],
			format_val_fn=lambda x: f"[red]{x['rate']:.6f}[/] /hr",
			header_name="Msgs/Hour",
			reverse=False, # Ascending order for lowest rate
			style="bright_red"
		)

		console.print(Columns([t3, t4], expand=True))
		console.print("\n")

if __name__ == "__main__":
	bot.run(os.getenv("TOKEN"))
