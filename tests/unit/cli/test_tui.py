from nasagent.cli.tui.app import NasaGentTui


async def test_tui_can_mount():
    app = NasaGentTui()
    async with app.run_test() as pilot:
        assert pilot.app is not None


async def test_tui_has_status_bar():
    app = NasaGentTui()
    async with app.run_test() as pilot:
        status = pilot.app.query_one("#status-repo")
        assert status is not None
        assert "repo" in str(status.render())


async def test_tui_has_info_panel():
    app = NasaGentTui()
    async with app.run_test() as pilot:
        info = pilot.app.query_one("#info-step")
        assert info is not None


async def test_tui_has_chat_log():
    app = NasaGentTui()
    async with app.run_test() as pilot:
        chat = pilot.app.query_one("#chat-log")
        assert chat is not None


async def test_tui_has_input():
    app = NasaGentTui()
    async with app.run_test() as pilot:
        inp = pilot.app.query_one("#chat-input")
        assert inp is not None


async def test_tui_exit_on_quit():
    app = NasaGentTui()
    async with app.run_test() as pilot:
        inp = pilot.app.query_one("#chat-input")
        inp.value = "exit"
        await inp.action_submit()
        await pilot.pause()
        assert app._exit
