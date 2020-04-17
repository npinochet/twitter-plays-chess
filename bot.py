import sys, json, os

import chess, chess.svg, chess.engine, redis
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM

from tweet import post_tweet, get_tweet, upload_image

state = "new_game"
default_thinking_time = 30
thinking_time_step = 10

redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
r = redis.from_url(redis_url)

header_msgs = {
	"new_game": "A brand new game vs de computer! I know you can beat him!",
	"continue": "What would the best move be [think emoji], vote for the next move!",
	"end_win": "Amazing! Twitter is the best chess player",
	"end_lost": "Aww :( better luck next game!",
	"end_draw": "It's a draw! nobody wins.",
}

move_msg = "{} {} to {}"
move_msg_prom = "{} {} to {} and promote {}"

def get_board():
	board = chess.Board()
	if r.exists("board"):
		state = "continue"
		board.set_fen(r.get("board"))
	return board

def get_next_move(board):
	if not r.exists("poll_ids"):
		return False

	poll_ids = json.loads(r.get("poll_ids"))

	max_count = -1
	max_label = ""

	for tweet in poll_ids:
		data = get_tweet(tweet)
		data = data["card"]["binding_values"]
		if not data["counts_are_final"]["boolean_value"]:
			sys.exit("Polls are not finished yet")

		for i in range(4):
			if "choice{}_label".format(i+1) not in data:
				break
			label = data["choice{}_label".format(i+1)]["string_value"]
			count = int(data["choice{}_count".format(i+1)]["string_value"])
			if count > max_count:
				max_count = count
				max_label = label

	if max_count <= 0: # No move is selected
		return False

	#parse label title
	sp = max_label.split(" ")
	f = sp[1].lower()
	t = sp[3].lower()
	p = ""
	if sp[-1].lower() in chess.PIECE_NAMES:
		p = chess.PIECE_SYMBOLS[chess.PIECE_NAMES.index(sp[-1].lower())]

	return chess.Move.from_uci(f+t+p)

def post_main_tweet(board):
	# generate board image
	img_path = "chess.png"
	with open("chess.svg", "w") as f:
		f.write(chess.svg.board(board=board))
	renderPM.drawToFile(svg2rlg("chess.svg"), img_path, fmt="PNG")

	media_id = upload_image(img_path)
	return post_tweet(header_msgs[state], media_id=media_id)

def post_options(board, tweet_id):
	order = [chess.QUEEN, chess.KING, chess.ROOK, chess.BISHOP, chess.KNIGHT, chess.PAWN]
	moves = {chess.piece_name(p).title(): [] for p in order}
	piece_map = board.piece_map()

	for m in list(board.legal_moves):
		piece = chess.piece_name(piece_map[m.from_square].piece_type).title()
		moves[piece].append(m)

	poll_ids = []

	for p in moves:
		if len(moves[p]) <= 0:
			continue

		op = []
		for m in moves[p]:
			f = chess.square_name(m.from_square).upper()
			t = chess.square_name(m.to_square).upper()
			if m.promotion:
				prom = chess.piece_name(m.promotion).title()
				op.append(move_msg_prom.format(p, f, t, prom))
				continue
			op.append(move_msg.format(p, f, t))

		# Make sure we don't leave a poll with only 1 options (tweeter doesn't accept this)
		if len(op) % 4 == 1:
			op.append("---")

		op = [op[i:i + 4] for i in range(0, len(op), 4)]

		head_tweet_id = post_tweet(p + " Moves:", reply_id=tweet_id, entries=op.pop(0))

		if head_tweet_id:
			poll_ids.append(head_tweet_id)
		for poll_ops in op:
			head_tweet_id = post_tweet(p + " cont...", reply_id=head_tweet_id, entries=poll_ops)
			if head_tweet_id:
				poll_ids.append(head_tweet_id)

	return poll_ids

def end_game(board):
	state = "end_draw"
	think_time = default_thinking_time
	if r.exists("AI_thinking_time"):
		think_time = int(r.get("AI_thinking_time"))

	res = board.result()

	if res == "1-0":
		state = "end_win"
		r.set("AI_thinking_time", str(think_time + thinking_time_step))
	elif res == "0-1":
		state = "end_lost"
		r.set("AI_thinking_time", str(max(0, think_time - thinking_time_step)))

	if r.exists("board"):
		r.delete("board")
	if r.exists("poll_ids"):
		r.delete("poll_ids")

	post_main_tweet(board)
	sys.exit("Game Done")

if __name__ == "__main__":
	board = get_board()
	move = get_next_move(board)
	if move:
		board.push(move)

	if board.turn == chess.BLACK and not board.is_game_over(True):
		engine = chess.engine.SimpleEngine.popen_uci(["python3", "sunfish/uci.py"])
		think_time = default_thinking_time
		if r.exists("AI_thinking_time"):
			think_time = int(r.get("AI_thinking_time"))
		result = engine.play(board, chess.engine.Limit(time=think_time))
		engine.quit()
		board.push(result.move)

	if board.is_game_over(True):
		end_game(board)

	tweet_id = post_main_tweet(board)
	poll_ids = post_options(board, tweet_id)
	r.set("poll_ids", json.dumps(poll_ids))
	r.set("board", board.fen())