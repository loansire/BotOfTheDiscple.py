# -*- coding: utf-8 -*-
"""Faux objets Discord minimalistes pour tester les moteurs de publication
sans réseau : un bot, des serveurs, des salons qui mémorisent leurs messages."""
from __future__ import annotations

import itertools
from contextlib import contextmanager
from types import SimpleNamespace
from unittest import mock

import discord

_ids = itertools.count(1000)


def _not_found() -> discord.NotFound:
    return discord.NotFound(SimpleNamespace(status=404, reason="Not Found"), "Unknown Message")


class FakeView:
    """Remplaçant de LayoutView : mémorise les items ajoutés (ping injecté)."""

    def __init__(self, label: str):
        self.label = label
        self.items: list = []

    def add_item(self, item):
        self.items.append(item)


class FakeMessage:
    def __init__(self, channel, *, content=None, view=None, files=None):
        self.id = next(_ids)
        self.channel = channel
        self.content = content
        self.view = view
        self.files = files or []

    async def delete(self):
        self.channel.messages.pop(self.id, None)

    async def edit(self, *, view=None, attachments=None):
        self.view = view
        self.files = attachments or []


class FakeChannel:
    def __init__(self, channel_id: int):
        self.id = channel_id
        self.messages: dict[int, FakeMessage] = {}

    async def send(self, content=None, *, view=None, files=None, **_):
        msg = FakeMessage(self, content=content, view=view, files=files)
        self.messages[msg.id] = msg
        return msg

    async def fetch_message(self, message_id: int):
        try:
            return self.messages[int(message_id)]
        except KeyError:
            raise _not_found() from None

    @property
    def pings(self) -> list[str]:
        return [m.content for m in self.messages.values() if m.content]


class FakeGuild:
    def __init__(self, guild_id: int, channels: dict[int, FakeChannel]):
        self.id = guild_id
        self.name = f"guild-{guild_id}"
        self.channels = channels


class FakeBot:
    def __init__(self, guilds: list[FakeGuild]):
        self.guilds = {g.id: g for g in guilds}

    def get_guild(self, guild_id: int):
        return self.guilds.get(int(guild_id))


@contextmanager
def subscriptions(topic: str, entries: dict[str, tuple[str, str | None]]):
    """Abonnements simulés : {guild_id: (channel_id, role_id)} pour `topic`."""

    def fake_iter(t):
        if t != topic:
            return iter(())
        return iter([(g, c, {"is_thread": False, "role": r}) for g, (c, r) in entries.items()])

    def fake_resolve(guild, dest_id, is_thread):
        return guild.channels.get(int(dest_id))

    with mock.patch("bot.publishing.primitives.iter_subscribers", fake_iter), \
            mock.patch("bot.publishing.primitives.resolve_destination", fake_resolve):
        yield
