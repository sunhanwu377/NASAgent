from nasagent.config.settings import NasAgentSettings
from nasagent.memory.manager import MemoryManager
from nasagent.platform.context import create_platform_context
from nasagent.plugins.commands import register_memory_commands


class FakeLlm:
    async def complete(self, messages):
        return "ok"

    def stream_complete(self, messages):
        raise NotImplementedError


def _make_ctx(tmp_path):
    ctx = create_platform_context(settings=NasAgentSettings())
    mgr = MemoryManager(tmp_path, FakeLlm())
    mgr.ensure_session("default")
    register_memory_commands(ctx, mgr)
    return ctx


class TestSessionCommands:
    def test_new(self, tmp_path):
        r = _make_ctx(tmp_path).commands.dispatch("/session new proj")
        assert r.exit_code == 0
        assert "proj" in r.message

    def test_list(self, tmp_path):
        ctx = _make_ctx(tmp_path)
        ctx.commands.dispatch("/session new a")
        ctx.commands.dispatch("/session new b")
        r = ctx.commands.dispatch("/session list")
        assert "a" in r.message
        assert "b" in r.message

    def test_switch(self, tmp_path):
        ctx = _make_ctx(tmp_path)
        ctx.commands.dispatch("/session new first")
        r = ctx.commands.dispatch("/session switch first")
        assert r.exit_code == 0

    def test_delete(self, tmp_path):
        ctx = _make_ctx(tmp_path)
        ctx.commands.dispatch("/session new temp")
        r = ctx.commands.dispatch("/session delete temp")
        assert r.exit_code == 0


class TestRememberCommands:
    def test_adds_entry(self, tmp_path):
        r = _make_ctx(tmp_path).commands.dispatch("/remember likes dark mode")
        assert r.exit_code == 0

    def test_lists_entries(self, tmp_path):
        ctx = _make_ctx(tmp_path)
        ctx.commands.dispatch("/remember test memory")
        r = ctx.commands.dispatch("/memories")
        assert "test memory" in r.message

    def test_forgets_entry(self, tmp_path):
        ctx = _make_ctx(tmp_path)
        ctx.commands.dispatch("/remember temp mem")
        r = ctx.commands.dispatch("/memories")
        line = r.message.strip().split("\n")[1]
        mem_id = line.strip().split(":")[0]
        r2 = ctx.commands.dispatch(f"/forget {mem_id}")
        assert r2.exit_code == 0


class TestPreferenceCommands:
    def test_set_get(self, tmp_path):
        ctx = _make_ctx(tmp_path)
        ctx.commands.dispatch("/pref set lang zh")
        assert "zh" in ctx.commands.dispatch("/pref get lang").message

    def test_list(self, tmp_path):
        ctx = _make_ctx(tmp_path)
        ctx.commands.dispatch("/pref set a 1")
        r = ctx.commands.dispatch("/pref list")
        assert "a" in r.message

    def test_delete(self, tmp_path):
        ctx = _make_ctx(tmp_path)
        ctx.commands.dispatch("/pref set key val")
        ctx.commands.dispatch("/pref delete key")
        assert "(not set)" in ctx.commands.dispatch("/pref get key").message
