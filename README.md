# spidy 2.0

This will be the second version of the spidy Web Crawler.

It will build on the framework of version 1 but will mostly be written
from scratch.

![cover.png](./cover.png)


# Index

  - [Top](#spidy-2-0)
  - [Index](#index)
  - [Notes](#notes)


***



## Notes

* GUI (cross-platform)
* Command-line arguments
* Create map of crawled internet
* As few imports from outside libraries as possible
* Cleaner, shorter code than 1.0
* Improvements from 1.0:
  - Need different logging/verbosity levels
  - Ability to log date for long crawls
  - Set storage and memory limits
  - Scan for available config files and offer as options
  - Better, more formal documentation
  - Cleaner multithreading
* Check HTTP status code first!
* Trap detection and avoidance
* Different politeness levels:
  - Robots.txt
  - Request timeouts
* Safely close on `KeyboardInterrupt`

Problems faced in Spidy 1.0 (as found in GitHub Issues):

* Robots.txt being queried every time
  - Needed to store in a database
* Accepted incorrect inputs and took default
  - Added validity check
* Individual threads saving where entire crawl should pause and save
* Errors when trying to parse empty pages
  - Added length check

Anticipated Errors:

* Incorrect robots.txt URL resulting in crawling everything
