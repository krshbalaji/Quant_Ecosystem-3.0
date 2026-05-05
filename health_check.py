from telegram_control import send_message

def main():
    try:
        send_message("Health check: system up ✅")
        print("Telegram OK")
    except Exception as e:
        print("Telegram FAILED:", e)

if __name__ == "__main__":
    print("Imports OK")
    main()