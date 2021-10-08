<p align="center">
  <a href="" rel="noopener">
 <img width=200px height=200px src="../assets/logos/logo.png?raw=true" alt="Project logo"></a>
</p>

<h3 align="center">Audnexus.bundle</h3>

<div align="center">

[![Status](https://img.shields.io/badge/status-active-success.svg)]()
[![GitHub Issues](https://img.shields.io/github/issues/djdembeck/Audnexus.bundle.svg)](https://github.com/djdembeck/Audnexus.bundle/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/djdembeck/Audnexus.bundle.svg)](https://github.com/djdembeck/Audnexus.bundle/pulls)
[![License](https://img.shields.io/badge/license-GNUGPL-blue.svg)](/LICENSE)
[![CodeFactor Grade](https://img.shields.io/codefactor/grade/github/djdembeck/Audnexus.bundle)](https://www.codefactor.io/repository/github/djdembeck/Audnexus.bundle)

</div>

---

<p align="center"> An Audnexus client for audiobooks using Plex's legacy plugin agent system.
    <br> 
</p>

## 📝 Table of Contents

- [About](#about)
- [Getting Started](#getting_started)
- [Configuring](#config)
- [Contributing](../CONTRIBUTING.md)

## 🧐 About <a name = "about"></a>

The aim of this project is to automate as much as possible, and make some intelligent, transparent choices for the user. All data used by this plugin is sourced from the parent aggregator, [audnex.us](https://github.com/djdembeck/audnexus). 

Files are expected/tested with common audiobook [file structure](https://support.plex.tv/articles/200265296-adding-music-media-from-folders/) and tags, specifically from either [Bragi Books](https://github.com/djdembeck/bragibooks) or [Seanap's guide](https://github.com/seanap/Plex-Audiobook-Guide).

## 🏁 Getting Started <a name = "getting_started"></a>

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See [deployment](#deployment) for notes on how to deploy the project on a live system.

### Prerequisites

- Plex Media Server `v1.24.4.5081` or greater.
- `git` installed on system, as this is the preferred method of installing/updating the agent. You can also extract the zip instead.

### Installing

A step by step series of examples that tell you how to get a development env running.

First, clone (or unzip) this project into your Plex `Plug-ins` directory:

```
git clone https://github.com/djdembeck/Audnexus.bundle.git
```
For future updates, run the below commmand from within `Audnexus.bundle`

```
git pull
```

Next, restart your Plex Media Server.

## 🔧 Configuing the agent <a name = "config"></a>

If you wish to use local tags/images, you can follow the directions [here](https://github.com/seanap/Plex-Audiobook-Guide#configure-metadata-agent-in-plex), but this agent assumes you will not.

### Create an audiobook library

- From within Plex Web, create a new library, with the MUSIC type, and name it Audiobooks.
- Add your folders.

In the ADVANCED tab:
- Scanner: `Plex Music Scanner`
- Agent: `Audnexus Agent`
- Toggle agent settings as you please.
- Uncheck all boxes except `Store track progress`
- Genres: `Embedded tags`
- Album Art: `Local Files Only`

Add the library and go do anything but read a physical book while the magic happens :)

### Migrate an existing audiobook library

If you are coming from another Audiobooks agent, such as Audiobooks.bundle, then upgrading is super easy!

- First, follow the steps for the ADVANCED tab above and save the settings.
- Second, go to the Audiobooks library settings, `Manage Library > Refresh All Metadata`. This will programmatically upgrade authors, and then every album under those authors.

Just like adding a new library, upgrading one can take some time to switch all your data over.