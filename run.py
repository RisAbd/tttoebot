#!/usr/bin/env python3

from telegram import telegram
import os, sys
import itertools as IT
import functools as FT
import operator as OP
import random


class Messages:
    HELP_REPLY = '''/new - to start new Tic Tac Toe Game
/start - to start bot
/help - to get help with commands'''

    START_REPLY = f'''Hello {{user.first_name}}, this is Tic Tac Toe Game Bot

{HELP_REPLY}'''

    UNKNOWN_REPLY = '''misunderstood: {text}

/help - for help'''

    NEW_GAME_REPLY = '''Let's play! Your turn'''


def chunks(it, n):
    """Yield successive n-sized chunks from l."""
    assert n > 0
    y = []
    for i in it:
        y.append(i)
        if len(y) != n:
            continue
        yield y
        y = []

# assert list(chunks(range(6), 2)) == [[0, 1], [2, 3], [4, 5]]


class Game:
    X = 'X'
    O = 'O'
    _NONE = ' '

    FIRST = X

    PLAYERS = X, O

    _EMPTIES = ('', '_', '-', ' ', None, False, 0)

    def __init__(self, *vals, data=None, first=FIRST):
        if vals:
            assert data is None
            assert len(vals) in (3, 9, 1)
            assert all(isinstance(v, str) for v in vals)
            if len(vals) == 1:
                (v, ) = vals
                assert len(v) == 9
                vals = [v[i*3:(i+1)*3] for i in range(3)]
            if len(vals) == 9:
                vals = [vals[i*3:(i+1)*3] for i in range(3)]
            assert all(len(v) == 3 for v in vals)
            data = list(map(list, vals))
        if data is None:
            assert not vals
            data = [[self._NONE for i in range(3)] for i in range(3)]

        assert len(data) == 3 and sum(map(len, data)) == 9

        for i, r in enumerate(data):
            for j, v in enumerate(r):
                if v in self._EMPTIES:
                    v = self._NONE
                else:
                    v = v.upper()
                data[i][j] = v

        self.data = data
        self.first = first
        self._last_turn = None

    @classmethod
    def from_reply_markup(cls, m: telegram.InlineKeyboardMarkup):
        r = [[None] * 3 for i in range(3)]
        for i, row in enumerate(m.inline_keyboard):
            for j, b in enumerate(row):
                r[i][j] = b.text
        return cls(data=r)

    def _value_to_human(self, v, _i=None):
        if v in self._EMPTIES:
            return self._NONE
        assert v in self.PLAYERS
        if self._last_turn is not None:
            v = v.lower()
        if _i == self._last_turn:
            v = v.upper()
        return v

    def __str__(self):
        it = enumerate(IT.chain.from_iterable(self.data))
        it = map(lambda i: self._value_to_human(i[1], _i=i[0]), it)
        it = map(' {} '.format, it)
        _1, _2, _3 = map('|'.join, chunks(it, 3))
        dl = '-'*11
        return '\n'.join((_1, dl, _2, dl, _3))

    def __repr__(self):
        return '\n'.join(map(repr, self.data))

    def _count(self, v):
        assert v in self.PLAYERS
        return list(filter(lambda v: v in self.PLAYERS, IT.chain.from_iterable(self.data))).count(v)

    @property
    def current(self):
        cx, co = map(self._count, self.PLAYERS)
        eq = cx == co
        r = (self.X, self.O) if self.first == self.X else (self.O, self.X)
        return r[0] if eq else r[1]

    @property
    def winner(self):
        for p in self.PLAYERS:
            # diagonal left-top to bottom-right
            if [self.data[i][i] for i in range(3)].count(p) == 3:
                return p
            # diagonal left-top to bottom-right
            if [self.data[i][2-i] for i in range(3)].count(p) == 3:
                return p
            for r in self.data:
                if r.count(p) == 3:
                    return p
            for i in range(3):
                if [self.data[j][i] for j in range(3)].count(p) == 3:
                    return p

    @property
    def is_draw(self):
        assert self.winner is None
        return not any(filter(lambda v: v in self._EMPTIES, IT.chain.from_iterable(self.data)))

    def turn(self, p, *t):
        assert len(t) in (2, 1)
        assert all(isinstance(c, int) for c in t)
        x, y = t if len(t) == 2 else (t[0]//3, t[0]%3)
        assert self.winner is None
        assert p in self.PLAYERS
        assert p == self.current
        assert self.data[x][y] in self._EMPTIES
        self.data[x][y] = p
        self._last_turn = x*3+y
        w = self.winner
        if w:
            return w

    def __eq__(self, o):
        if not isinstance(o, type(self)):
            return NotImplemented
        return self.data == o.data

    @property
    def markup(self):
        return telegram.InlineKeyboardMarkup.from_rows_of(
            buttons=[
                telegram.InlineKeyboardMarkup.Button(text=v, callback_data=i)
                for i, v in enumerate(IT.chain.from_iterable(self.data))
            ],
            items_in_row=3,
        )

    def auto_turn(self, p=None, r=True):
        assert r, 'todo: make smart turns'
        if p is None:
            p = self.current
        assert not self.is_draw and self.winner is None
        empty_coords = list(map(OP.itemgetter(0), filter(lambda v: v[1] in self._EMPTIES, enumerate(IT.chain.from_iterable(self.data)))))
        random.shuffle(empty_coords)
        return self.turn(p, next(iter(empty_coords)))


def test():
    assert Game.from_reply_markup(Game().markup) == Game()
    assert isinstance(Game().markup, telegram.InlineKeyboardMarkup)

    assert Game().current == Game.X
    assert Game(first=Game.O).current == Game.O

    assert Game().turn('X', 0, 0) is None
    assert Game('XO-', 'XO-', '---').turn('X', 2, 0) == 'X'
    assert Game('XX-', 'OO-', '---').turn('X', 0, 2) == 'X'
    assert Game('XO-', 'OX-', '---').turn('X', 2, 2) == 'X'
    assert Game('-OX', 'OX-', '---').turn('X', 2, 0) == 'X'

    assert Game('XXO', 'OOX', 'XXO').is_draw
    assert Game('XXO', 'OOX', 'XX-') == Game(*'XXOOOXXX_') == Game('XXOOOXXX ')

    try:
        Game('X--------').turn('X', 0, 0)
    except AssertionError:
        pass

    g = Game()
    for i in range(5):
        # print(g)
        print(g.auto_turn())

    # sys.exit()

test()


def on_update(bot: telegram.Bot, update: telegram.Update):
    if update.type == telegram.Update.Type.MESSAGE:
        msg: telegram.Message = update.message
        chat = msg.chat
        if msg.bot_command == '/start':
            bot.send_message(
                chat=chat,
                text=Messages.START_REPLY.format(user=msg.from_),
            )
        elif msg.bot_command == '/help':
            bot.send_message(
                chat=chat,
                text=Messages.HELP_REPLY,
            )
        elif msg.bot_command == '/new':
            bot.send_message(
                chat=chat,
                text=Messages.NEW_GAME_REPLY,
                reply_markup=Game().markup,
            )
        else:
            bot.send_message(
                chat=chat,
                text=Messages.UNKNOWN_REPLY.format(text=msg.text),
            )
    elif update.type == telegram.Update.Type.CALLBACK_QUERY:
        cq: telegram.CallbackQuery = update.callback_query
        chat = cq.message.chat
        game = Game.from_reply_markup(cq.message.reply_markup)
        turn = int(cq.data)
        try:
            winner = game.turn(game.first, turn)
        except AssertionError:
            bot.send_message(chat=chat, text='wrong turn')
            return
        else:
            if winner:
                bot.send_message(chat=chat, text='you won!\ntype /new for new game')
            elif game.is_draw:
                bot.send_message(chat=chat, text='draw ):\ntype /new for new game')
            else:
                winner = game.auto_turn(game.O)
                if winner:
                    bot.send_message(chat=chat, text='i won! B)\ntype /new for new game')
                elif game.is_draw:
                    bot.send_message(chat=chat, text='draw ):\ntype /new for new game')
                else:
                    bot.send_message(
                        chat=chat,
                        text='your turn',
                        reply_markup=game.markup,
                    )


def main():
    try:
        bot = telegram.Bot.by(os.environ['BOT_API_TOKEN'])
    except KeyError:
        return sys.exit('BOT_API_TOKEN env variable required')

    last_update = None
    while True:
        updates = bot.updates(after=last_update, timeout=3)
        print('updates:', len(updates))
        for u in updates:
            on_update(bot, u)
            last_update = u


if __name__ == "__main__":
    main()
