"""nyaa.si module"""

import sys
import logging
from torrench.utilities.Config import Config

class NyaaTracker(Config):
    """
    Nyaa.si class.

    This class fetches results from nyaa.si
    and displays in tabular form.
    Selected torrent is downloaded to hard-drive.

    Default download location is $HOME/Downloads/torrench

    Known problems:
    - If the torrent name in the website is too long (200 chars+) the table will be displayed incorrectly in the terminal.
    Possible fixes:
    - Cut the name if the name is too big.
    """

    def __init__(self, title: str):
        """Class constructor"""
        Config.__init__(self)
        self.title = title
        self.logger = logging.getLogger('log1')
        self.output_headers = ['NAME', 'INDEX', 'SIZE', 'S', 'L']
        self.index = 0
        self.mapper = []
        self.proxy = self.check_proxy('nyaa')
        self.search_parameter = "/?f=0&c=0_0&q={query}&s=seeders&o=desc".format(query=self.title)
        self.soup = self.http_request(self.proxy+self.search_parameter)

    def check_proxy(self, proxy: str):
        """
        Check for proxies in the `config.ini` file.
        :params: proxy
        :returns: proxy on success, -1 on error
        """
        _torrench_proxies = self.get_proxies(proxy)
        counter = 0
        if _torrench_proxies:
            for proxy in _torrench_proxies:
                print("Testing: {proxy}".format(proxy=self.colorify("yellow", proxy)))
                proxy_soup = self.http_request(proxy+'/?f=0&c=0_0&q=hello&s=seeders&o=desc')
                self.logger.debug("Testing {proxy} as a possible candidate.".format(proxy=proxy))
                if not proxy_soup.find_all('td', {'colspan': '2'}):
                    print("{proxy} was a bad proxy. Trying next proxy.".format(proxy=proxy))
                    counter += 1
                    if counter == len(_torrench_proxies):
                        self.logger.debug("Proxy list finished. No valid proxies were found.")
                        print("Failed to find any valid proxies. Terminating.")
                        return -1
                else:
                    print("Proxy `{proxy}` is available. Connecting.".format(proxy=proxy))
                    self.logger.debug("Proxy `{proxy}` is a valid proxy.")
                    return proxy
        print("No proxies were given.")
        return -1

    def parse_data(self):
        data = content.find_all('tr')
        return data

    def parse_name(self):
        """
        Parse torrent name
        """
        t_names = []
        for name in self.soup.find_all('td', {'colspan': '2'}):
            t_names.append(name.get_text().replace('\n', ''))
        if t_names:
            return t_names
        print("Unable to parse torrent name.")
        sys.exit(2)

    def parse_urls(self):
        t_urls = []
        for url in self.soup.find_all('a'):
            try:
                if url.get('href').startswith('/download/'):
                    t_urls.append(self.colorify('yellow', 'https://nyaa.si'+url['href']))
            except AttributeError:
                pass
        if t_urls:
            return t_urls
        print("Unable to parse torrent URLs.")
        sys.exit(2)

    def parse_magnets(self):
        t_magnets = []
        for url in self.soup.find_all('a'):
            try:
                if url['href'].startswith('magnet:'):
                    t_magnets.append(url['href'])
            except KeyError:
                pass
        if t_magnets:
            return t_magnets
        print("Unable to parse magnet links.")
        sys.exit(2)

    def parse_sizes(self):
        t_size = []
        for size in self.soup.find_all('td', {'class': 'text-center'}):
            if size.get_text().endswith(("GiB", "MiB")):
                t_size.append(self.colorify("yellow", size.get_text()))
            else:
                pass
        if t_size:
            return t_size
        print("Unable to parse size of files.")
        sys.exit(2)

    def parse_seeds(self):
        t_seeds = []
        for seed in self.soup.find_all('td', {'style': 'color: green;'}):
            t_seeds.append(self.colorify("green", seed.get_text()))
        if t_seeds:
            return t_seeds
        print("Unable to parse seeds")
        sys.exit(2)

    def parse_leeches(self):
        t_leeches = []
        for leech in self.soup.find_all('td', {'style': 'color: red;'}):
            t_leeches.append(self.colorify("red", leech.get_text()))
        if t_leeches:
            return t_leeches
        print("Unable to parse leechers")
        sys.exit(2)

    def fetch_results(self):
        """
        Fetch results for a given query.

        @datafanatic:
        Work in progress
        """
        print("Fetching results")
        self.logger.debug("Fetching...")
        self.logger.debug("URL: %s", self.url)
        try:
            name = self.parse_name()
            urls = self.parse_urls()
            sizes = self.parse_sizes()
            seeds = self.parse_seeds()
            leeches = self.parse_leeches()
            magnets = self.parse_magnets()
            self.index = len(name)
        except (KeyError, AttributeError) as e:
            print("Something went wrong. Logging and terminating.")
            self.logger.exception(e)
            print("OK. Terminating.")
        if self.index == 0:
            print("No results were found for the given query. Terminating")
            self.logger.debug("No results were found for `%s`.", self.title)
            return -1
        self.logger.debug("Results fetched. Showing table.")
        self.mapper.insert(self.index, (name, urls, magnets))
        return list(zip(name, ["--"+str(idx)+"--" for idx in range(1, self.index+1)], sizes, seeds, leeches))

    def select_torrent(self):
        """
        Select torrent from table using index.
        """
        while True:
            try:
                prompt = int(input("(0 to exit)\nIndex > "))
                self.logger.debug("Selected index {idx}".format(idx=prompt))
                if prompt == 0:
                    print("Bye!")
                    break
                else:
                    selected_index, download_url, magnet_url = self.mapper[0][0][prompt-1], self.mapper[0][1][prompt-1], self.mapper[0][2][prompt-1]
                    print("Selected torrent [{idx}] - {torrent}".format(idx=prompt,
                                                                        torrent=selected_index))
                    print("Magnet link: {magnet}".format(magnet=self.colorify("red", magnet_url)))
                    print("Upstream link: {url}".format(url=download_url))
                    self.copy_magnet(magnet_url)
                    option = input("Load magnet link to client? [y/n] ")
                    if option.lower() in ['yes', 'y']:
                        try:
                            self.logger.debug("Loading torrent to client")
                            self.load_torrent(magnet_url)
                        except Exception as e:
                            print("Something went wrong! See logs for details.")
                            self.logger.exception(e)
                            continue
                    else:
                        self.logger.debug("NOT loading torrent to client.")
                        pass                    
            except IndexError as e:
                self.logger.exception(e)
                print("Invalid index.")

    def get_torrent(self, url, name):
        """
        Download the .torrent file to the computer.
        """
        self.download(url, name+'.torrent')

def main(title):
    """
    Execution will begin here.
    """
    try:
        print("[Nyaa.si]")
        nyaa = NyaaTracker(title)  
        results = nyaa.fetch_results()
        nyaa.show_output([result for result in results], nyaa.output_headers)
        nyaa.select_torrent()
        #print(nyaa.mapper)
    except KeyboardInterrupt:
        nyaa.logger.debug("Interrupt detected. Terminating.")
        print("Terminated")

if __name__ == "__main__":
    main('naruto')