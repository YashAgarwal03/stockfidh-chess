from flask import Flask, render_template, request, jsonify
import chess
from stockfish import Stockfish
import logging

def white():
    app = Flask(__name__)
    app.logger.setLevel(logging.DEBUG)

    try:
        stockfish = Stockfish(
            path=r"stockfish\stockfish-windows-x86-64-avx2.exe",
            depth=18,
            parameters={"Threads": 2, "Skill Level": 20}
        )
        app.logger.info("Stockfish initialized successfully")
    except Exception as e:
        app.logger.error(f"Stockfish init error: {str(e)}")
        raise

    board = chess.Board()

    @app.route('/')
    def setup():
        return render_template('setup.html')

    @app.route('/game')
    def game():
        return render_template('index.html')

    @app.route('/new-game', methods=['POST'])
    def new_game():
        nonlocal board, stockfish
        board.reset()
        difficulty = int(request.form['difficulty'])
        stockfish.set_skill_level(difficulty)
        stockfish.set_fen_position(board.fen())
        app.logger.info(f"New game started with difficulty {difficulty}")
        return jsonify({"fen": board.fen()})

    @app.route('/move', methods=['POST'])
    def handle_move():
        nonlocal board, stockfish
        try:
            data = request.get_json()
            from_sq = data['from']
            to_sq = data['to']
            difficulty = data['difficulty']

            # Validate it's White's turn
            if board.turn != chess.WHITE:
                return jsonify({"error": "Not your turn", "fen": board.fen()})

            move = chess.Move.from_uci(f"{from_sq}{to_sq}")
            if move not in board.legal_moves:
                return jsonify({"error": "Illegal move", "fen": board.fen()})

            # Execute player move
            board.push(move)
            app.logger.info(f"Player moved: {move.uci()}")

            # Stockfish (Black) response
            response = {}
            if not board.is_game_over():
                stockfish.set_skill_level(difficulty)
                stockfish.set_fen_position(board.fen())
                best_move = stockfish.get_best_move()
                stockfish_move = chess.Move.from_uci(best_move)
                board.push(stockfish_move)
                response['stockfish_move'] = best_move
                app.logger.info(f"Stockfish moved: {best_move}")

            response.update({
                "fen": board.fen(),
                "status": get_game_status()
            })
            return jsonify(response)

        except Exception as e:
            app.logger.error(f"Move error: {str(e)}")
            return jsonify({"error": str(e), "fen": board.fen()}), 500

    def get_game_status():
        if board.is_checkmate():
            return "Checkmate! You " + ("won!" if board.turn == chess.BLACK else "lost!")
        if board.is_stalemate():
            return "Stalemate!"
        return "Check!" if board.is_check() else ""

    return app


app = white()

if __name__ == "__main__":
    app.run(debug=True)

