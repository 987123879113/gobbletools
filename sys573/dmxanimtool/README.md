# dmxanimtool

This tool renders the videos from Sys573 Dance Maniax games (2nd Mix and 2nd Mix Append J-PARADISE only).

## Prerequisites
- Python 3 (tested on 3.9.6)
- Java Runtime Environment (tested with openjdk 17.0.6, other recent versions should work too)
- [jPSXdec](https://github.com/m35/jpsxdec/releases)
- [sys573tool](https://github.com/987123879113/gobbletools/tree/master/sys573/sys573tool)
- [py573a](https://github.com/987123879113/gobbletools/tree/master/sys573/py573a)

## Setup
Install python3 requirements:
```sh
python3 -m pip install -r requirements.txt
```

Extract the jPSXdec binary zip downloaded from the [official releases](https://github.com/m35/jpsxdec/releases) page into the `tools/jpsxdec` folder. Your path should look like `tools/jpsxdec/jpsxdec.jar` if done correctly.

Additional, follow the build steps for sys573tool and py573a to get those working for the following steps.
## How to prepare data

1. (Optional if using a MAME CHD) Extract CHD to CUE/BIN using chdman
```sh
chdman extractcd -i game.chd -o game.cue
```
2. Extract contents of cue/bin (or your CD image or physical CD) to a separate folder.
3. Use [sys573tool](https://github.com/987123879113/gobbletools/tree/master/sys573/sys573tool) to extract the GAME.DAT
```sh
python3 sys573tool.py --mode dump --input game_cd_contents --output game_data_extracted
```
This dumps all of the game's internal flash contents to the `game_data_extracted` folder.

4. Decrypt all of the MP3 .DATs using [py573a](https://github.com/987123879113/gobbletools/tree/master/sys573/py573a)
```sh
(Linux/macOS)
find game_cd_contents/DAT -type f -iname "*.dat" -exec python3 py573a.py --input "{}" \;

(Windows)
for %s in (game_cd_contents/DAT/*.dat) do python3 py573a.py --input "%s"
```
5. (Optional) Prepare video cache. This step may take a significant amount of time so be prepared to wait potentially an hour. Alternatively, the video animation renderer tool will cache the videos it needs on demand if they aren't in the cache already. Letting the tool cache what's needed is recommended if you don't plan on rendering every song.
```sh
python3 video_frame_cacher.py -i game_cd_contents/MOV -i game_data_extracted
```
Expect a full frame cache for each specific game to be somewhere around 2gb-3gb each.

I would recommend creating a new cache folder for every individual game you want to render so as to not run into issues where a video may have changed in some way between game releases. You can use the `-o frame_cache_folder_name` parameter to specify the output cache folder.
```sh
python3 video_frame_cacher.py -i game_cd_contents/MOV -i game_data_extracted -o frame_cache_folder_name
```
### How to render video using anim_renderer.py
```sh
python3 anim_renderer.py -r game_cd_contents/MOV -r game_data_extracted -m game_data_extracted -s game_cd_contents/DAT -c frame_cache_folder_name -i song_id
```

Replace the `song_id` value at the end with the 4/5 letter song ID for the song you wish to render. See below for a full list of songs available in the supported games.

## Rendered Video FPS (15 fps vs 60 fps)

The videos are played back at 15 fps in-game, but this tool defaults to saving the videos as 60 fps. There is a difference that you must be aware of when you decide to render the videos. Some songs, for example `boom`, will look much more fluid during some parts at 60 fps when the movie script makes use of `PlayBeat`/`PlayBeat2` commands, which internally are calculated differently from the other playback commands allowing them to render in-between frames that normally get skipped in the actual game.

If you would prefer a more arcade accurate video render then you can specify to save the videos as 15 fps using the `--fps 15` parameter.

## Song ID list
This is a reference to find the correct song ID for a song. The artists and titles are taken from the game's internal music database so they may be written differently compared to how they're shown in-game.

```
abso  | dj TAKA - ABSOLUTE (ABSOLUTE)
afro  | 8 bit - AFRONOVA PRIMEVAL (AFRONOVA PRIMEVAL)
aint  | Tomoki Hirata - Ain't It Good (Original Vocal Mix) (Ain't It Good (Original Vocal Mix))
alln  | Tomoki Hirata - All Night featuring Angel (Original Mix) (All Night (Original Mix))
bail  | DANDY MINEIRO - BAILA! BAILA! (BAILA! BAILA!)
beto  | NI-NI - BE TOGETHER (BE TOGETHER)
bfor  | NAOKI - B4U (B4U)
body  | Tomoki Hirata - Body featuring JD Braithwaite (I.C.B. Club Vocal Mix) (Body (I.C.B. Club Vocal Mix))
boom  | KING KONG & D.JUNGLE GIRLS - BOOM BOOM DOLLAR (Red Monster 2000 Mix) (BOOM BOOM DOLLAR)
boss  | Non Stop Mix Special - Jet World + DROP OUT + PARANOiA MAX TYPE 2 (Non Stop Mix Special 1)
boss2 | Non Stop Mix Special - PARANOiA jazzy groove + TRIP MACHINE CLIMAX + DEAD END (Non Stop Mix Special 2)
boys  | SMILE.dk - BOYS (Euro Mix) (BOYS (Euro Mix))
brok  | NAOKI feat.PAULA TERRY - BROKEN MY HEART (BROKEN MY HEART)
butt  | SMILE.dk - BUTTERFLY (KCP FUNG-FU MIX) (BUTTERFLY (KCP FUNG-FU MIX))
cats  | E-ROTIC - CAT'S EYE (Ventura Mix) (CAT'S EYE (Ventura Mix))
cbos0 | Non Stop Mix Special - PARANOiA jazzy groove + TRIP MACHINE CLIMAX + DEAD END (ny edit) (Non Stop Mix Special 2 (ny edit))
cbos1 | Non Stop Mix Special - PARANOiA jazzy groove + TRIP MACHINE CLIMAX + DEAD END (sy edit) (Non Stop Mix Special 2 (sy edit))
cbos2 | Non Stop Mix Special - PARANOiA jazzy groove + TRIP MACHINE CLIMAX + DEAD END (yh edit) (Non Stop Mix Special 2 (yh edit))
cbos3 | Non Stop Mix Special - PARANOiA jazzy groove + TRIP MACHINE CLIMAX + DEAD END (os edit) (Non Stop Mix Special 2 (os edit))
cbos4 | Non Stop Mix Special - PARANOiA jazzy groove + TRIP MACHINE CLIMAX + DEAD END (ss edit) (Non Stop Mix Special 2 (ss edit))
cbos5 | Non Stop Mix Special - PARANOiA jazzy groove + TRIP MACHINE CLIMAX + DEAD END (tt edit) (Non Stop Mix Special 2 (tt edit))
damd  | JOGA - DAM DARIRAM (B4 ZA BEAT Mix) (DAM DARIRAM (B4 ZA BEAT Mix))
disc  | Tomosuke * SABRINA - ALL MY LOVE (ALL MY LOVE)
dome  | DJ MOjo - DO ME (MONDO DISCO ITALO STYLE) (DO ME (MONDO DISCO ITALO STYLE))
dood  | CARTOONS - DOODAH! (K.O.G. Re-edit) (DOODAH! (K.O.G. Re-edit))
drlo  | Asuka M. - Dr.Love (Dr.Love)
dxye  | TaQ - DXY! (DXY!)
dyna  | NAOKI - DYNAMITE RAVE (B4 ZA BEAT MIX) (DYNAMITE RAVE (B4 ZA BEAT MIX))
eaty  | ANGIE GOLD - EAT YOU UP (Phat k Mix) (EAT YOU UP (Phat k Mix))
ente  | B3-PROJECT - ENTER THE DRAGON (G'z Island Mix) (ENTER THE DRAGON (G'z Island Mix))
fore  | CAPTAIN JACK - TOGETHER AND FOREVER (KCP Euro Mix) (TOGETHER AND FOREVER)
funk  | SPAKER - FUNKY MODELLING (FUNKY MODELLING)
gorg  | THE SURRENDERS - GORGEOUS 2012 (GORGEOUS 2012)
heav  | Hiro feat.Sweet little 30's - Heaven is a '57 metallic gray (gimmix) (Heaven is a '57 metallic gray)
horn  | BRASS TRICKS - GET IT ALL (GET IT ALL)
hotl  | JOHN DESIRE - HOT LIMIT (HOT LIMIT)
indi  | T.E.M.P.O. feat.Mohammad & Emi - jane jana (jane jana)
inmy  | REBECCA - IN MY DREAMS (IN MY DREAMS)
itgo  | K.Wit feat.Anthony Shoemo - KEEP IT GOING (KEEP IT GOING)
itsa  | BASTAMIKE & RASHAD - IT'S A PARTY (IT'S A PARTY)
iwil  | TAEKO + THE V.O.W - I WILL FOLLOW HIM (I WILL FOLLOW HIM)
juna  | BAMBEE - 17才 (17才)
keep  | N.M.R-typeG - KEEP ON MOVIN' (DMX MIX) (KEEP ON MOVIN' (DMX MIX))
kick  | BUS STOP - KICK THE CAN (HYPER KCP MIX) (KICK THE CAN (HYPER KCP MIX))
kiss  | NAOKI feat.SHANTI - KISS KISS KISS (KISS KISS KISS)
lets  | JT PLAYAZ - LET'S GET DOWN (MO-FUNK MIX) (LET'S GET DOWN (MO-FUNK MIX))
loco  | ALEXIA - LOCOMOTION (LOCOMOTION)
mats  | RE-VENGE - 祭 (J-SUMMER MIX) (祭 (J-SUMMER MIX))
meal  | NAOKI J-STYLE feat.MIU - Kiss me all night long (Kiss me all night long)
mean  | K.Wit feat.GARY - MEANING OF LIFE (MEANING OF LIFE)
meet  | EDDY HUNTINGTON - MEET MY FRIEND (B4 ZA BEAT Mix) (MEET MY FRIEND (B4 ZA BEAT Mix))
mind  | TOMOSUKE - Mind Parasite (Mind Parasite)
mobo  | Orange Lounge - Mobo*Moga (Mobo*Moga)
odor  | CAPTAIN JACK - おどるポンポコリン (おどるポンポコリン)
peti  | SMILE.dk - PETIT LOVE (PETIT LOVE)
punk  | THE INFECTION - MAD BLAST (MAD BLAST)
puty  | UZI-LAY - PUT YOUR FAITH IN ME (SATURDAY NIGHT MIX) (PUT YOUR FAITH IN ME)
quic  | dj TAKA - Quickening (Quickening)
rhyt  | CJ CREW FEATURING CHRISTIAN D - RHYTHM AND POLICE (RHYTHM AND POLICE)
robo  | Brian Morris feat.Thomas - VIRTUAL MIND (VIRTUAL MIND)
roma  | JUDY CRYSTAL - ロマンスの神様 (ロマンスの神様)
russ  | ES44 - Happy-hopper (Happy-hopper)
sanc  | Osamu Kubota - sanctus (sanctus)
stay  | emi - STAY (Organic house Version) (STAY (Organic house Version))
stay2 | TOMOSUKE - STAY (Mod bouncy Version) (STAY (Mod bouncy Version))
sync  | JOE RINOIE - SYNCHRONIZED LOVE (Red Monster Hyper Mix) (SYNCHRONIZED LOVE)
thet  | THE TWIST (Double Pump MIX) (THE TWIST (Double Pump MIX))
toge  | CYDNEY D - TOGETHER FOREVER (TOGETHER FOREVER)
toky  | JUDY CRYSTAL - TOKYO ALL READY (TOKYO ALL READY)
tubt  | CHUMBAWAMBA - TUBTHUMPING (KCP Happy Mix) (TUBTHUMPING (KCP Happy Mix))
twin  | FinalOffset - Twin Bee -Generation X- (Twin Bee -Generation X-)
upsi  | COO COO - UPSIDE DOWN (Hyper Euro Mix) (UPSIDE DOWN (Hyper Euro Mix))
wond  | MM - WONDA (SPEED K MIX) (WONDA (SPEED K MIX))
```