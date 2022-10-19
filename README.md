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

<p align="center"> An <a href="https://github.com/djdembeck/audnexus">audnex.us</a> client, providing rich author and audiobook data to Plex via its legacy plugin agent system.
    <br> 
</p>

## 📝 Table of Contents

- [About](#about)
- [Getting Started](#getting_started)
- [Configuring](#config)
- [Usage](#usage)
- [Contributing](CONTRIBUTING.md)

## 🧐 About <a name = "about"></a>

The aim of this project is to automate as much as possible, and make some intelligent, transparent choices for the user. All data used by this plugin is sourced from the parent aggregator, [audnex.us](https://github.com/djdembeck/audnexus). By using the audnexus API, searches and matches, which are cached, are greatly accelerated over scraping each search and item page from HTML. Additionally, the API can have multiple sources of data used for each book entry.

Audnexus will first search a book/author to see if it's come across it before. If it's found, it returns them straight away. If not, it requests that the aggregator import all the available data. Thus, the more people who use audnexus' client plugins, the faster the API will be and more data complete. You can also run a fork of the API yourself, see the above repo on how to do that.

Available regions:
- `[au]` - `.com.au`
- `[ca]` - `.ca`
- `[de]` - `.de`
- `[es]` - `.es`
- `[fr]` - `.fr`
- `[in]` - `.in`
- `[it]` - `.it`
- `[jp]` - `.co.jp`
- `[us]` - `.com`
- `[uk]` - `.co.uk`

***NOTE***: The agent was built for English-based regions. If you find an issue with your region, please open a new issue or PR.

## 🏁 Getting Started <a name = "getting_started"></a>

Getting the agent up and running is a very smooth process, whether this is your first foray into audiobooks or you are migrating a library from another audiobooks agent. We look forward to getting you high quality data!

### Prerequisites

- Plex Media Server `v1.24.4.5081` or greater.
- `git` installed on system, as this is the preferred method of installing/updating the agent. You can also extract the zip instead.
- Files are expected to be in/tested with common audiobook [file structure](https://support.plex.tv/articles/200265296-adding-music-media-from-folders/) and tags, specifically from either [Bragi Books](https://github.com/djdembeck/bragibooks) or [Seanap's guide](https://github.com/seanap/Plex-Audiobook-Guide). In particular, you are expected to have the following structure: `Author Name/Book Name/Book Name: Subtitle.m4b` with `album` and `albumartist` tags. This is imperative for proper matching!

### Installing

If you are new to getting plugins on your system or do not have access to `git`, go through this Plex documentation: [How do I manually install a plugin?
](https://support.plex.tv/articles/201187656-how-do-i-manually-install-a-plugin/) If you are already familiar with the plugins system, and have `git`, follow the below steps.

1. Clone (or unzip) this project into your Plex `Plug-ins` directory:

```
git clone https://github.com/djdembeck/Audnexus.bundle.git
```

2. Restart your Plex Media Server.

For future updates, run the below commmand from within the `Audnexus.bundle` folder.

```
git pull
```

## 🔧 Configuring the agent <a name = "config"></a>

If you wish to use local tags/images, you can follow the directions [here](https://github.com/seanap/Plex-Audiobook-Guide#configure-metadata-agent-in-plex), but this agent assumes you will not.

### Using quick match

There are currently 2 quick match/search override options:
- **ASIN**: Bypasses search and explicitly uses the ASIN Provided
- **Region** (ie `[uk]`): Searches the given region instead of your set region.

Quick match supports filename and manual search.

This works for both authors and books. By default, the ASIN is searched in your library's `region` (from agent settings).

You may override region on a per author/book basis using the region code in brackets, such as `[uk]` either before or after the other search terms.

Here are some quick match examples:

- Override region
```
[uk] NAME
```
- Override asin and region
```
[uk] B01234ABCD
```
- Override ASIN and Region from filename
```
Author Name/Book Name B01234ABCD [uk]/Book Name: Subtitle.m4b
```

***NOTE***: Authors cannot be quick matched from filenames.

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

## 🎈 Usage <a name="usage"></a>

### Manually fixing matches
There are a few tricks to know about using fix match for books and authors:
- You may use [Quick Match](#using-quick-match) if you already know the ASIN.
- Some authors do not have an Audible profile. These will not have an Audnexus DB entry.
- You may need to modify author names in search to find them (for example, removing a middle initial). This is a search limitation we are looking to improve.
- Book results come back in the format of: `"TITLE" by AUTHOR_FIRSTINITIAL.AUTHOR_LASTNAME w/ NARRATOR_FIRSTINITIAL.NARRATOR_LASTNAME`
- Year field cannot be used by music agents (what we use), so it's an irrelevant parameter.
- Scores are based on the following criteria: Book title ([Levenshtein distance](https://en.wikipedia.org/wiki/Levenshtein_distance)), Author(s) name ([Levenshtein distance](https://en.wikipedia.org/wiki/Levenshtein_distance)), language of book vs language of library (2 points), and 1 point deduction for each result (relevance score).
- Identical results for book may appear. Typically the one with a score of `100` is the 'correct' one.

### Data that the agent brings to your library:

#### Authors (Artists)
- High resolution image.
- Text description/bio.
- Genres
- Sorted by `Last Name, First Name`
- Combines books with multiple authors into the first author, reducing duplicate author entries/pages.

#### Books (Albums)
- High resolution cover (up to 3200x3200).
- Rating (currently based on Audible user rating).
- Release date.
- Record label (publisher)
- Review (plot summary)
- Genres and sub-genres:
  - Up to 2 parent category genres.
  - Up to 4 sub-category genres.
- Narrator as `Style` tag.
- Authors as `Mood` tag.
- Series as `Mood` tag (prefixed by `Series:`)
- Sorted by Series number and then book title.

Collections are not available to legacy agents. Please do not open requests for them.