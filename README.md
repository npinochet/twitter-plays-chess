# Twitter Plays Chess

A [Twitter bot](https://twitter.com/EveryoneChess) to play chess against a computer using polls.

## How to run
`python bot.py`

A single run will:
* Get the current board using Redis
* Get the results of the last polls (program exits if polls aren't closed)
* Make the AI play (against [Stockfish](https://stockfishchess.org/))
* Check if the game is over
* Post new board and polls

## How I managed to make Twitter polls

As a base I used [airhadoken's gist](https://gist.github.com/airhadoken/8742d16a2a190a3505a2) for creating polls. I also got my Twitter Api Keys using twurl and the Twitter for Mac Consume Key found [here](https://gist.github.com/shobotch/5160017).
