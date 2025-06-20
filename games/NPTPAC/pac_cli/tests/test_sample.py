from games.NPTPAC.pac_cli.app.core.config_manager import ConfigManager
from games.NPTPAC.pac_cli.app.core.lily_persona_handler import LilyPersonaHandler
from games.NPTPAC.pac_cli.app.core.ner_handler import NERHandler


def test_config_manager_loads_defaults(tmp_path):
    cm = ConfigManager(npt_base_dir=tmp_path)
    assert isinstance(cm.settings, dict)
    assert "lily_core_memory" in cm.settings


def test_ner_handler_lists_categories(tmp_path):
    ner_dir = tmp_path / "ner_repository"
    ner_dir.mkdir()
    (ner_dir / "00_CORE_EDICTS").mkdir()
    nh = NERHandler(ner_root_path=ner_dir)
    cats = nh.list_categories()
    assert "00_CORE_EDICTS" in cats


def test_lily_persona_handler_init(tmp_path):
    # Setup config manager with a valid LilyCoreMemory path
    lcm_dir = tmp_path / "LilyCoreMemory"
    lcm_dir.mkdir()
    config = ConfigManager(npt_base_dir=tmp_path)
    config.settings["lily_core_memory"] = {"base_path": str(lcm_dir)}
    handler = LilyPersonaHandler(config_manager=config)
    assert handler.lcm_base_path == lcm_dir
