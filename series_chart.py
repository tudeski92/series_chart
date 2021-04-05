from bs4 import BeautifulSoup
import requests
import numpy as np
import matplotlib.pyplot as plt
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import logging


class Mylogger:

    def __init__(self, stream=False, filename="logs.txt"):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(level=logging.INFO)
        self.obj = None
        formatter = logging.Formatter("%(asctime)s : %(filename)s : Line %(lineno)d : %(message)s")
        handler = logging.StreamHandler() if stream else logging.FileHandler(filename)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)



imdb_log = Mylogger(stream=True)

class ImdbSoup:

    def __init__(self, url):
        self.req_url = requests.get(url).text
        self.soup_data = BeautifulSoup(self.req_url, "lxml")
        self.title = self.soup_data.find("div", class_="title_wrapper").h1.text.strip()
        imdb_log.logger.info(self.title)
        self.series_data = dict()

    def get_seasons(self):
        seasons_div_1 = self.soup_data.find("div", class_="seasons-and-year-nav")
        seasons_div_2 = seasons_div_1.find_all("div")
        seasons_href = [href.find_all("a") for href in seasons_div_2 if len(href.find_all("a")) != 0 ]
        seasons_nums = [nums.text for nums in seasons_href[0]]
        seasons_links = [[f"https://www.imdb.com{links['href']}"] for links in seasons_href[0]]
        seasons_tuple = zip(seasons_nums, seasons_links)
        sorted_seasons_tuple = sorted(seasons_tuple, key=lambda x: x[0])
        self.series_data = {self.title: dict(sorted_seasons_tuple)}

    def get_rates(self):
        self.get_seasons()
        for season_num, season_link in self.series_data[self.title].items():
            html_data = requests.get(season_link[0]).text
            episode_soup = BeautifulSoup(html_data, "lxml")
            episode_details_list = episode_soup.find("div", class_="list detail eplist")
            episode_data = episode_details_list.find_all("div", class_="info")
            episode_number = [episode.find("div").text for episode in episode_details_list.find_all("div", class_="hover-over-image zero-z-index")]
            episode_titles = [episode.find("a").text for episode in episode_data if episode.find("div", class_="ipl-rating-widget") is not None]
            episode_rates = [float(episode.find("div", class_="ipl-rating-star small").find("span", class_="ipl-rating-star__rating").text)
                             for episode in episode_data if episode.find("div", class_="ipl-rating-widget") is not None]
            self.series_data[self.title][season_num].append(list(zip(episode_number, episode_titles, episode_rates)))
        imdb_log.logger.info(self.series_data)

    def get_dict_all_episodes(self):
        all_episodes = {}
        for season_num, episode_list in self.series_data[self.title].items():
            for data, title, rate in episode_list[1]:
                all_episodes[title] = (data, rate)
        return all_episodes

    def get_max_rated_title(self):
        titles = list(self.get_dict_all_episodes().keys())
        rates = [value[1] for value in self.get_dict_all_episodes().values()]
        season_epp_num = [value[0] for value in self.get_dict_all_episodes().values()]
        max_rate = max(rates)
        max_rate_indexes = [index + 1 for index, value in enumerate(rates) if value == max_rate]
        max_rate_titles = [titles[index - 1] for index in max_rate_indexes]
        max_rate_list = [max_rate for _ in range(len(max_rate_indexes))]
        max_season_epp_num = [season_epp_num[index - 1] for index in max_rate_indexes]
        imdb_log.logger.info(f"Max rated: {max_rate_titles}")
        return zip(max_rate_list, max_rate_titles, max_rate_indexes, max_season_epp_num)


    def get_min_rated_title(self):
        titles = list(self.get_dict_all_episodes().keys())
        rates = [value[1] for value in self.get_dict_all_episodes().values()]
        season_epp_num = [value[0] for value in self.get_dict_all_episodes().values()]
        min_rate = min(rates)
        min_rate_indexes = [index + 1 for index, value in enumerate(rates) if value == min_rate]
        min_rate_titles = [titles[index - 1] for index in min_rate_indexes]
        min_rates_list = [min_rate for _ in range(len(min_rate_indexes))]
        min_season_epp_num = [season_epp_num[index - 1] for index in min_rate_indexes]
        imdb_log.logger.info(min_rate_titles)
        return zip(min_rates_list, min_rate_titles, min_rate_indexes, min_season_epp_num)


class RatesBarChart:

    def __init__(self, imdb):
        self.imdb = imdb
        self.imdb.get_rates()
        imdb_log.logger.info("Creating chart")

    def create_plot(self):
        rates = [value[1] for value in self.imdb.get_dict_all_episodes().values()]
        max_tuple = self.imdb.get_max_rated_title()
        min_tuple = self.imdb.get_min_rated_title()
        y = np.array(rates)
        x = np.arange(1, len(rates) + 1)
        x_tick = np.arange(1, len(rates), 2)
        plt.title(self.imdb.title)
        plt.figure(figsize=(45, 4.8))
        plt.scatter(x, y, color="green")
        plt.plot(x, y, color="blue", label=self.imdb.title)
        plt.legend(loc='upper left', frameon=True, prop={'size': 20})
        plt.xlabel("Episode", fontsize=20)
        plt.ylabel("Rate", fontsize=20)
        plt.xticks(x_tick)
        for max_rate, title, episode, season_epp in max_tuple:
            plt.annotate(f" {season_epp} {title} {max_rate}", (episode, max_rate))
        for min_rate, title, episode, season_epp in min_tuple:
            plt.annotate(f" {season_epp} {title} {min_rate}", (episode, min_rate))
        plt.grid(True)
        plt.savefig("out.png", bbox_inches='tight')


class Final:

    def __init__(self, url):
        firefox_options = Options()
        firefox_options.add_argument("--headless")
        self.driver = webdriver.Firefox(firefox_options=firefox_options)
        imdb_log.logger.info(f"Getting {url}")
        self.driver.get(rf"{url}")
        assert "DuckDuckGo" in self.driver.title
        imdb_log.logger.info(f"{url} obtained successfully")

    def return_series_url(self, title):
        search_box = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.NAME, "q")))
        search_box.clear()
        search_box.send_keys(f"{title} series imdb")
        search_box.submit()
        elements = WebDriverWait(self.driver, 10).until(EC.visibility_of_all_elements_located((By.XPATH, '//*[@id="links"]')))
        links = [element.text for element in elements][0].split("\n")
        link = [link for link in links if "www.imdb.com" in link][0]
        imdb_log.logger.info(f"Current url: {link}")
        self.driver.close()
        return link

    def create_chart(self, title):
        url = self.return_series_url(title)
        imdb = ImdbSoup(url)
        chart = RatesBarChart(imdb)
        chart.create_plot()


final = Final("https://www.duckduckgo.pl")
title = input("Title: ")
final.create_chart(title)



