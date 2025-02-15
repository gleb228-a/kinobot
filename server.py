from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# Endpoint для основного бота
@app.route('/cinemabot', methods=['POST'])
async def cinemabot_webhook():
    from cinemabot import process_update
    update_data = request.get_json(force=True)
    if not update_data:
        return jsonify({"status": "error", "message": "Empty request"}), 400
    try:
        await process_update(update_data)
    except Exception as e:
        print(f"Error processing update for CinemaBot: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"status": "ok"}), 200

# Endpoint для админ-бота
@app.route('/adminbot', methods=['POST'])
async def adminbot_webhook():
    from adminbot import process_update
    update_data = request.get_json(force=True)
    if not update_data:
        return jsonify({"status": "error", "message": "Empty request"}), 400
    try:
        await process_update(update_data)
    except Exception as e:
        print(f"Error processing update for AdminBot: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"status": "ok"}), 200

# Проверка работы сервера
@app.route('/')
def index():
    return "Bots are running!"

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
    