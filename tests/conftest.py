from unittest.mock import MagicMock, PropertyMock
import pytest

from utils import AsyncMock
import platform
from plugin import EpicPlugin
from process_watcher import ProcessWatcher
from consts import LAUNCHER_PROCESS_IDENTIFIER

PRODUCT_MAPPING_RESPONSE = {"fn":"fortnite","ut":"unreal-tournament","crab":"satisfactory","min":"hades","wren":"ashen","vpr":"shadow-complex","odin":"robo-recall","ark":"ark","helloneighbor":"hello-neighbor","squad":"squad","vrfunhouse":"vr-funhouse","darkandlight":"dark-and-light","mars2030":"mars-2030","bussim18":"bus-sim-18","conanexiles":"conan-exiles","wex":"battle-breakers","pixark":"pixark","battalion":"battalion","showmaker":"showmaker","marmoset":"rebel-galaxy-outlaw","puma":"genesis-alpha-one","moose":"super-meat-boy-forever","wombat":"world-war-z","turtle":"maneater","lemur":"journey","morpho":"hello-neighbor-hide-and-seek","starfish":"outerwilds","springbok":"darksiders3","jaguar":"subnautica","buffalo":"super-meat-boy","nautilus":"vampyr","foxglove":"subnautica-below-zero","kestrel":"donut-county","meerkat":"gorogoa","badger":"what-remains-of-edith-finch","ocelot":"walking-dead-final-season","impala":"the-division-2","cobra":"my-time-at-portia","puffin":"axiom-verge","feverfew":"jackbox-party-pack-1","lilac":"jackbox-party-pack-2","newt":"spellbreak","jackal":"dauntless","yarrow":"flower","orchid":"jackbox-party-pack-3","bloodroot":"walking-dead-season-one","buttercup":"walking-dead-season-two","begonia":"walking-dead-a-new-frontier","tulip":"thimbleweed-park","snowdrop":"jackbox-party-pack-4","geranium":"jackbox-party-pack-5","snapdragon":"metro-exodus","daisy":"drawful-2","plumeria":"shakedown-hawaii","hibiscus":"oxenfree","weaver":"rebel-galaxy","iris":"phoenix-point","clary":"assassins-creed-odyssey","camellia":"assassins-creed-origins","hellebore":"far-cry-3","sundrop":"for-honor","pansy":"dangerous-driving","carnation":"rainbow-six-siege","hyacinth":"ghost-recon-wildlands","angelonia":"watch-dogs-2","larkspur":"far-cry-primal","8b9fc0e3ee7d478abc047d1a3596c568":"far-cry-3-blood-dragon","silene":"close-to-the-sun","azalea":"thecycle","d0d1b5541a6540d5a81daacb3324639b":"rime","daffodil":"omen-of-sorrow","corydalis":"slime-rancher","viola":"outward","rose":"kine","c5e786eddfd041caa9984213e3f9621d":"metro-last-light-redux","petunia":"metro-2033-redux","calluna":"control","rosemallow":"the-outer-worlds","amaranth":"ancestors","protea":"industries-of-titan","lavender":"beyond-two-souls","columbine":"detroit-become-human","adenium":"afterparty","oleander":"journey-to-the-savage-planet","cosmos":"rune-2","4561b40e52584ac2bcf34bbd5c401480":"overcooked","catnip":"borderlands-3","canna":"rollercoaster-tycoon-adventures","anemone":"world-of-goo","lily":"operencia","middlemist":"the-sinking-city","nemesia":"vampire-the-masquerade-bloodlines-2","magnolia":"the-witness","sweetpea":"trover-saves-the-universe","clover":"little-inferno","allium":"observation","basil":"human-resource-machine","holly":"7-billion-humans","fennel":"walking-dead-michonne","oregano":"anno-1800","bc81d1e7d1794d3a94e4dbf26e92166d":"transistor","anise":"assassins-creed-3","599d248ca46b45a8b40a3b4e484712cb":"the-crew-2","a646020cb93b4ea995cda70647bbe001":"steep","fa234e40c4d44dfa84fbcb302fef0233":"city-of-brass","cinnamon":"sherlock-holmes-the-devils-daughter","d0545b136bb042fb9014e72b6af748f6":"ghostbusters-the-video-game-remastered","313f3719063340f886d90e70ae503cd4":"stories-untold","a0f2d82a52534f278c558f99f00e3219":"magic-leap","2dbd2f64abdc4bbab077424d5c85e01b":"ghost-recon-breakpoint","a9dad8af015a422eb89a5f88e6def923":"the-pathless","72dda1cee6e040c1bbce452bd501e0a7":"diesel-brothers-truck-building-simulator-editor","a9cb15d3362d43d585b8a5b13b8a4513":"johnwickhex","04467b70295342a79381467353f23955":"layers-of-fear","aster":"heavy-rain","935fa66c485e4c988eb939f86dc458b5":"phantom-brigade","85398892cc4544088ee87c673f95bb6f":"observer","387bc8d3398a40f7ae14de417b4acefc":"innerspace","5d582c08e31a43128a61093a2c3ff7f0":"shenmue-3","0e87bed2a83c4cf6a68a7aeb43f25cf0":"kingdom-new-lands","bd46d4ce259349e5bd8b3ded20274737":"chivalry-2","77f2b98e2cef40c8a7437518bf420e47":"cyberpunk-2077","be13f6c4fb11427fbf3313ce93b97cc0":"enter-the-gungeon","ed355406eacb4633a648f682ddb492b8":"castlestorm2","dfd2530e80e4425d801913b0879be444":"zombie-army-4-dead-war","37baf50c268d47779020d73143bb02b0":"auto-chess","28dde12d84ef45b8b321dbc962c1b217":"falcon-age","3ade24028e9247039924d3877af0a2ea":"what-the-golf","fe5a2e3e842a4394938a81f3308df2ed":"solar-ash-kingdom","0a84818055e740a7be21a2e5b6162703":"watch-dogs-legion","f7e06ee3d0c1491094cc0215859f0120":"untitled-goose-game","ada169f07b81464a9fc06a7d6896101d":"the-sojourn","phlox":"griftlands","d0230ef21b1f4ef29aec0d49946912fc":"torchlight","ff1cd8b38bda4f6281879c9bdb228ff1":"atomicrops","4b35838425c74992ad42e1276b2161ca":"gods-and-monsters","sunflower":"helium-rain","13bb5776b9e1424d84ce42d9ba61c0ca":"inside","92053006068e4aa9b1ad413f72090f5e":"limbo","4fd85a772cd5471aa5e38efcaa0d6f24":"last-day-of-june","76339caf9e8e4d24b62761c736e82b42":"tetris-effect","bec822fb982843c3be794d440728336b":"moonlighter","91189432bbad4478afd611edff7f0339":"this-war-of-mine","00b9ec358e1f46daa4f8e1194d5081d8":"alan-wake","b9def67e597b4be7a16146146a044d02":"mechwarrior-5","4d2a12aff0484d699b1806ab104d259b":"alan-wake-american-nightmare","19078740fbcc4eada59a5a4ae7b3724c":"gnog","b534830f4c524447bfd2266ce70cf8ab":"walking-dead-definitive-series","4756b80eb0f74d45b77922e54052cfed":"mutant-year-zero","62d6f15b1bb345f6a42585b4c8c847a0":"hyper-light-drifter","41f47fd0d3e248bc938a5815d6d64daa":"fez","7f498fbf0a4e43239d58eee6615ae806":"readyset-heroes","84f45b7676af47d9adecd3b636466f89":"the-settlers","b671fbc7be424e888c9346a9a6d3d9db":"celeste","5fdcc0dc67294af3be740f362bd976fd":"mtg-arena","413361d2d5db4912ac2dfbcf27a38141":"ooblets","7af7476ff9eb4a8d9cd9d6486224de76":"abzu","015763e579d4479cb1ef7780bf91804f":"manifold-garden","lupine":"wattam","6cec00f8934146508b884b0f139d55d0":"superliminal","530eeeaffca14275a451d7cff61ee6bb":"the-end-is-nigh","e1809e1742cb498080d8849b11a99c5a":"airborne-kingdom","fa0c74ef7780498fb222dcd099bf82a2":"the-eternal-cylinder","c0783fd957634390af33808d1a1f56dd":"no-straight-roads","6ac9ddab8e604e3ba2d4ea01e8f9fa7d":"conarium","f6dcd5bf17c0469789292d1166bf91a1":"wrc-8","2bfd5ca43ef443739ada168e017e1b78":"cardpocalypse","argyle":"trials-rising","933ada2ec45e4184ae840d64c99e0ba9":"rogue-company","854ca270c7f04fe483212a35811e9189":"everything","bec57b5341ad4294b005a7dd18691419":"yaga","e5e30c728f1947759251eb5283ffa6e3":"batman-arkham-knight","cb23c857ec0d42d89b4be34d11302959":"lego-batman-2","843c8ce683474448bb104a9651e8f325":"lego-batman","5f7c811695f14b8fa3a8e1ea35713d23":"batman-arkham-asylum","40c34bea9cd0460589c867f6a7246342":"batman-arkham-city","83022e1b4c304addb2aadee1db854f8d":"lego-batman-3","0fb229f35a3f4eb788b05ae91419a214":"arise-a-simple-story","1093790870b043cdbae03d91d76d9ae6":"rainbow-six-quarantine","96ccba8fe8e649dfa6f96cee11e625e1":"atlas-mod-kit","d759128018124dcabb1fbee9bb28e178":"surviving-mars","43605e89e49d438485298819a7ef17b4":"minit","95b4d5a753d042678f775d5e1eb5ab25":"surviving-the-aftermath","b69961c88cb446a395ace83341dd94cc":"bee-simulator","4b5f1eb366dc45f0920d397c01b291ba":"q-u-b-e-2","8a6a94901c8248fca1f5c78931c85cbd":"soma","c77e320376c14aa68121bffb108721c7":"a-knights-quest","752368fdba244e9386023cfb2b9d6ceb":"the-messenger","4fece418b513465d9416a700db869585":"jackbox-party-pack-6","b30b6d1b4dfd4dcc93b5490be5e094e5":"red-dead-redemption-2","coriander":"far-cry-5","cumin":"far-cry-new-dawn","d1479d6f93fa4e6ca4415e83a7a5d703":"costume-quest","74d82b28ab424956ac24407229fe6faa":"ruiner","742f165671424189aecdfdadf5ea9755":"nuclear-throne","e509c16d53714b13ba8e393966507255":"star-wars-jedi-fallen-order","f4a904fcef2447439c35c4e6457f3027":"death-stranding","aa5ef9d2f8394731a034504c562e292c":"bad-north","nutmeg":"supermash","fc8d1547232045f6a23257cfd04ef3e8":"rayman-legends","8f8bddb3ff464536984ce8e945cb5f8c":"south-park-the-stick-of-truth","764eb429792649e4a606413cd649de2c":"south-park-the-fractured-but-whole","25ef88acc7f34afc8ac6669e11573882":"bloodroots","ba3149b6d7a7488ab5cc674154458757":"jotun","61bc780f42f84fe29e6dfee957ab82de":"the-escapists","f2bfff793b224f6190a394f461c9a4b8":"the-telltale-batman","a8f9fb4a881e47b489715f18f7d08e2f":"the-wolf-among-us","61449320f87347a8bf02159cbf8adb7f":"before-we-leave","fa11862b1cfd42e3b3c6395af46efe3e":"yooka-laylee-and-the-impossible-lair","5a82d5954a1943d79dc6b49cde2fe972":"predator-hunting-grounds","65add98d18a64e2ead3b8f05c84cba94":"the-red-lantern","5c0d568c71174cff8026db2606771d96":"into-the-breach","f7dc1618d0bd4810a61f50d44333900e":"faster-than-light","7f1fa336313d48eca0a802170aa8dd8a":"surgeon-simulator-2","52b90f9a982a404781b189f6a7903226":"totally-reliable-delivery-service","ca4058f18b0a4a9e9e2ccc28f7f33000":"kingdom-come-deliverance","4492ce99b4124b74a0bb83f78b3d70b8":"for-the-king","0aaf0617ee0d47df87c0dc93509159dd":"carcassonne","b4d9169e1b8548f2babec33107253309":"ticket-to-ride","a40f6c03e1374358809ec38c999059c0":"foregone","90c3f58497da48d789cc39bff57dc2f4":"overpass","908bed122ba84c4a908ee1e14da401c3":"superhot","8e66d3f552b448afb1889c32ac855fc9":"towerfall-ascension","6c77bc1b5faa4ac98441ec75cca0d320":"ape-out","ffe512fa1e594ee6a75d4643d1e21b43":"totally-accurate-battle-simulator","ca8077d80493497188e0ca5bca3ebe60":"sundered-eldritch-edition","2bc23fc2438c47ec8acb0641980f50c1":"darksiders","091d95ea332843498122beee1a786d71":"darksiders2","2f215955790d456b80c291bc2feaf7f7":"shadow-tactics","400cc6605aee41de88f976b587a48aa0":"the-talos-principle","8aa6e526d2864c108f219747ad7011e5":"horace","f9c2aedaff8442b286fbd026948b9f09":"faeria","493e9ad801e8487497fe7840cb8404bb":"farming-simulator-19","d5ee752640ef4cee8b7f5364410ba41f":"the-bridge","dcaca38045a049b2b50fba8a4dac4407":"days-of-war","cf87285950ba492bbdc370b9d265ea36":"far-cry-4","cbbb7e8728a3476f97e44f3856c3cb13":"anno-2205","3102f48ad7bd409ab6e34f2ad697e961":"corruption-2029","5b325322a4c04b9e9e780b9a1e9b2d70":"aztez","2744acda6a2e493e9894b389b6564df7":"snowrunner","c9be94273fe244c08032ca493ad87434":"assassins-creed-syndicate","aeac94c7a11048758064b82f8f8d20ed":"mount-and-blade-2"}


@pytest.fixture
def account_id():
    return "c531da7e3abf4ba2a6760799f5b6180c"


@pytest.fixture
def display_name():
    return "testerg62"


@pytest.fixture
def refresh_token():
    return "REFRESH_TOKEN"


@pytest.fixture
def authenticated():
    return PropertyMock()


@pytest.fixture
def http_client(account_id, refresh_token, authenticated):
    mock = MagicMock(spec=())
    type(mock).account_id = account_id
    type(mock).refresh_token = refresh_token
    type(mock).authenticated = authenticated
    mock.authenticate_with_exchange_code = AsyncMock()
    mock.authenticate_with_refresh_token = AsyncMock()
    mock.retrieve_exchange_code = AsyncMock()
    mock.close = AsyncMock()
    mock.set_auth_lost_callback = MagicMock()
    return mock


@pytest.fixture
def backend_client():
    mock = MagicMock(spec=())
    mock.get_display_name = MagicMock()
    mock.get_users_info = AsyncMock()
    mock.get_assets = AsyncMock()
    mock.get_catalog_items_with_id = AsyncMock()
    mock.get_owned_games = AsyncMock()
    mock.get_productmapping = AsyncMock()
    mock.get_productmapping.return_value = PRODUCT_MAPPING_RESPONSE
    return mock


@pytest.fixture
def process_watcher():
    process_watcher = ProcessWatcher(LAUNCHER_PROCESS_IDENTIFIER)
    return process_watcher


@pytest.fixture
def local_provider(process_watcher, mocker):
    mocker.patch("local.ProcessWatcher", return_value=process_watcher)
    mock = MagicMock()
    return mock


@pytest.fixture()
async def plugin(http_client, backend_client, local_provider, mocker):
    mocker.patch("plugin.AuthenticatedHttpClient", return_value=http_client)
    mocker.patch("plugin.EpicClient", return_value=backend_client)
    mocker.patch("plugin.LocalGamesProvider", return_value=local_provider)
    plugin = EpicPlugin(MagicMock(), MagicMock(), None)

    plugin.store_credentials = MagicMock()
    plugin.lost_authentication = MagicMock()

    yield plugin

    await plugin.shutdown()


@pytest.fixture()
async def authenticated_plugin(plugin, http_client, backend_client, mocker, account_id, refresh_token, display_name):
    http_client.authenticate_with_refresh_token.return_value = None
    backend_client.get_users_info.return_value = [{
        "id": "c531da7e3abf4ba2a6760799f5b6180c",
        "displayName": display_name,
        "externalAuths": {}
    }]
    backend_client.get_display_name.return_value = display_name
    mocker.patch.object(plugin, "store_credentials")
    await plugin.authenticate({"refresh_token": "TOKEN"})
    return plugin
