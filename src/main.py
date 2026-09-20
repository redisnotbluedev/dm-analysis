import discord, dotenv, rich, os, rich.progress, datetime, discord.http, asyncio, json
from discord.ext import commands

dotenv.load_dotenv()
bot = commands.Bot(command_prefix="!")
bot.has_run = False
dms = []

@bot.event
async def on_ready():
	print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")

	if not bot.has_run:
		bot.has_run = True

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
				hours = age.total_seconds() / 3600
				rate = messages / hours if hours > 0 else 0

				dms.append({
					"name": channel.recipient.name,
					"display_name": channel.recipient.display_name,
					"messages": messages,
					"age": age,
					"rate": rate
				})

				await asyncio.sleep(5)

		dms.sort(key=lambda x: x.get("rate"), reverse=True)
		with open("data.json", "w") as f:
			json.dump(dms, f)

		print("=== Top 10 ===")
		for idx, dm in enumerate(dms[:10]):
			print(f"#{idx + 1}: {dm["display_name"]}\n\t- {dm["rate"]} messages/hour\n\t- {dm["messages"]} total messages\n\t- Age: {dm["age"]}")

if __name__ == "__main__":
	bot.run(os.getenv("TOKEN"))
