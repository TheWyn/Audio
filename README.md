<h2 align="center">Audio Cog</h2>

[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/Drapersniper/Audio/master.svg)](https://results.pre-commit.ci/latest/github/Drapersniper/Audio/master)
[![CI status](https://github.com/Drapersniper/Audio/actions/workflows/main.yml/badge.svg)](https://github.com/Drapersniper/Audio/actions/workflows/main.yml)
[![LastCommit](https://img.shields.io/github/last-commit/Drapersniper/Audio?logo=Github&labelColor=292f35&logoColor=878f96&color=32c754)](https://github.com/Drapersniper/Audio/commits/master)
[![Contributors](https://img.shields.io/github/contributors/Drapersniper/Audio.svg?labelColor=292f35&logo=GitHub&logoColor=878f96&color=32c754)](https://github.com/Drapersniper/Audio/graphs/contributors)
[![License](https://img.shields.io/badge/License-GPLv3-blue.svg?labelColor=292f35&color=32c754)](https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/LICENSE)
[![Black](https://img.shields.io/badge/code%20style-black-000000.svg?labelColor=292f35&logo=python&logoColor=878f96&color=32c754)](https://github.com/psf/black)
[![iSort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=292f35&logo=python&logoColor=878f96&color=32c754)](https://pycqa.github.io/isort)
[![Python Version](https://img.shields.io/pypi/pyversions/Red-Discordbot?labelColor=292f35&logo=python&logoColor=878f96&color=32c754)](https://www.python.org/downloads/)
[![discord.py](https://img.shields.io/badge/discord-py-blue.svg?labelColor=292f35&logo=python&logoColor=878f96&color=32c754)](https://github.com/Rapptz/discord.py/)

[![Personal Patreon](https://img.shields.io/badge/Support-Me!-black.svg?labelColor=292f35)](https://www.patreon.com/drapersniper)
[![Discord](https://img.shields.io/discord/850282003425394699?color=7289da&label=Support%20Server&logo=Discord&style=plastic&labelColor=292f35&logoColor=878f96)](https://discord.gg/bdnjFPQQaZ)

# Modified Audio Cog by Draper

:wave: Hello there, I'm Draper the previous maintainer of Red's core Audio Cog.

This repository contains a heavily modded version of the core Audio cog, with several new features (Filters, Bundled EQ, Global settings to name a few), fixes and potentially new bugs :smile:

# Notice:
The Global Audio API service has not been discontinued, yes this is a direct contradiction to the [claim](https://github.com/Cog-Creators/Red-Status/issues/13) made by the organization Cog Creators and their [published change logs](https://docs.discord.red/en/latest/changelog_3_4_0.html#redbot-3-4-12-2021-06-17) and discord announcement.

The Global Audio API is a service that has been alive for over 2 years, long prior to it being used by the Cog Creators organization.

Cog Creators lost their ability to use the service, after the fact they have decided to make a claim about the Global API being discontinued, which is not true as the owner of the API will keep it alive and maintained as originally stated.

------------
## Requirements:
1. If you use an external instance you are required to use the following JAR:
    - <https://github.com/Drapersniper/Lavalink-Jars/releases/latest>
2. You need to ensure your application.yaml is up to date and has the same settings as <https://github.com/Drapersniper/Audio/blob/master/audio/data/application.yml>

------------
Installation
------------

Primarily, make sure you have `downloader` loaded.


    [p]load downloader

Next, let's add my repository to your system.


    [p]repo add audio https://github.com/Drapersniper/Audio

To install a cog, use this command.


    [p]cog install audio audio


## Notes
- This cog uses a heavily modded version of Red's Lavalink library:
  - Source code can be found here: https://github.com/Drapersniper/Red-Lavalink.
- This cog uses a heavily modified version of the JAR which Red users (With the ability to auto update and support for Java 13 among some of the new features.)
  - Releases can be found here: https://github.com/Drapersniper/Lavalink-Jars/releases

# License
Released under the [GNU GPL v3](https://www.gnu.org/licenses/gpl-3.0.en.html) license.

An original copy of the licence for the original Audio work can be seen in [LICENSE.old](LICENSE.old)
This version of Audio split with [Red's Audio](https://github.com/Cog-Creators/Red-DiscordBot/commit/ca373052c53d88ac87d89632e4328ac09e890190) on this commit.

# Why branching off Red.
I have been getting DM'ed a lot in the past 24 hours, so I wanted to clarify what happened.

First things first, myself leaving the Red server is a final decision, I don't need anyone reading this to cause create drama, in fact I do not want it, this is simply to clarify my actions so that it doesn't look like my decisions were due to a petty discussing in #AT.

Originally this repo was to serve as an alpha repository however going forward I will be maintaining a different version of Audio than the one bundled with Red and will not be contributing upstream.

The reason for this is due to a disagreement with Kowlin, the Lead Core developer in the Red project, I've been growing fed up with his toxicity and dictatorial attitude even more so due to him being hardly around for quite a while;
The interaction in Red's #advanced-testing channel yesterday was the tipping point where he abused his staff permissions and muted my bot while I was testing core feature, the reason given my him was "spam" and when I asked for him to unmute he said no and that I should take it up with @Twentysix if I was unhappy.

But alas, myself cutting ties with the project is not related to that singular interaction but his overall toxicity and appalling attitude towards others.
![image](https://user-images.githubusercontent.com/27962761/120639810-ac85eb80-c469-11eb-8fd9-3ef683b91028.png)
![image](https://user-images.githubusercontent.com/27962761/120640248-24ecac80-c46a-11eb-845f-f7c8373350fc.png)
![image](https://user-images.githubusercontent.com/27962761/120640343-48175c00-c46a-11eb-9a95-bd1e6ef43ac0.png)
![image](https://user-images.githubusercontent.com/27962761/120641323-616cd800-c46b-11eb-93b2-1042feca1b84.png)

Like I mentioned on my first PR closed I will be maintaining both this repo and the Red edge repo, as several users do use it.

The reason for me cutting all ties with org was Kowlin breaching the Org policies and everyone in org acting like he hasn't breached the policies;
![image](https://user-images.githubusercontent.com/27962761/120639036-d5f24780-c468-11eb-92fd-3fe0dd890b59.png)

The breach of said policy (abusing owner permission without due process) is ground for removal within the org.
![image](https://user-images.githubusercontent.com/27962761/120639954-d7703f80-c469-11eb-8dcb-37ba8f1d5bf5.png)

After My first closure Kowlin removed me from the QA team within the org without disgussing with Aika (The Lead QA as the policy requires him to do before taking action.)
![image](https://user-images.githubusercontent.com/27962761/120639227-0803a980-c469-11eb-8466-b61cbc1b8f85.png)

Yes there are some fundamental issues with Red, the repo, the main support server, the cog support server and the way org members, however Red is a great project and I do wish all the best for it.
I do hope Kowlin realises how shitty his attitude can be and how it is negatively affecting the community, as that is the best outcome for the project.

I will continue maintaining the Global API for Audio even if the Org wanted to revoke my access to it, because that is the best for Red users.
I will continue maintaining the Global API domain.
I will continue maintaining Edge as loads of users do depend on it.
I will continue maintaining this fork of Audio because users do depend on it.


Update:
Due to the org removing myself from it completely I've cut all ties with the org, which means the global api as it is will cease to exist.

Not to worry I will continue to provide the service to users of my audio, however if you use red Audio the api will cease to function for you.
