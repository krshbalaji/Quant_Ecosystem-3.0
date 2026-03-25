import datetime

today = datetime.date.today()

weekday = today.weekday()

print("\n📅 Today:", today)

# Thursday = 3

if weekday == 3:
    print("🔥 WEEKLY EXPIRY DAY → Trade Only Breakout Momentum")
elif weekday == 2:
    print("⚠️ Pre-Expiry Build-Up → Reduce Position Size")
elif weekday == 4:
    print("💧 Post Expiry Liquidity Vacuum → Trend Moves Possible")
else:
    print("✅ Normal Trading Day")