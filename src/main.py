import discord, dotenv, rich, os, rich.progress, datetime, discord.http, asyncio, json
from discord.ext import commands

dotenv.load_dotenv()
bot = commands.Bot(command_prefix="!")
has_run = False
dms = []

def format_seconds(seconds):
	days = int(seconds // 86400)
	hours = int((seconds % 86400) // 3600)
	if days > 0:
		return f"{days}d {hours}h"
	return f"{hours}h"

@bot.event
async def on_ready():
	global dms, has_run
	print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")

	if not has_run:
		has_run = True

		if os.path.exists("data.json"):
			print("Found existing data.json. Loading local cache...")
			with open("data.json", "r") as f:
				dms = json.load(f)
		else:
			print("No local cache found. Analysing DM channels...")
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

			dms.sort(key=lambda x: x.get("rate"), reverse=True)
			with open("data.json", "w") as f:
				json.dump(dms, f, indent=4)

		print("\n=== Top 10 ===")
		for idx, dm in enumerate(dms[:10]):
			age_seconds = dm.get("age_seconds", 0)
			age_display = format_seconds(age_seconds)
			print(f"#{idx + 1}: {dm["display_name"]}\n\t- {dm["rate"]:.4f} messages/hour\n\t- {dm["messages"]} total messages\n\t- Age: {age_display}")

if __name__ == "__main__":
	bot.run(os.getenv("TOKEN"))
