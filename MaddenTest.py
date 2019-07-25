from WinSharesTest import WinShares
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import requests


class MaddenTest():
    
    def __init__(self):
        self.year_to_madden = lambda year : str(int(year[-2:])+2)
        self.teams = {'nwe': 'Patriots', 'mia': 'Dolphins', 'buf': 'Bills', 'nyj': 'Jets', 'bal': 'Ravens', 'rav': 'Ravens', 'pit': 'Steelers', 'cle': 'Browns', 'cin': 'Bengals', 'hou': 'Texans', 'htx': 'Texans', 'clt': 'Colts', 'ind': 'Colts','oti': 'Titans', 'ten': 'Titans', 'jax': 'Jaguars', 'kan': 'Chiefs', 'sdg': 'Chargers', 'lac': 'Chargers', 'den': 'Broncos', 'rai': 'Raiders', 'oak': 'Raiders', 'dal': 'Cowboys', 'phi': 'Eagles', 'was': 'Redskins', 'nyg': 'Giants', 'chi': 'Bears', 'min': 'Vikings', 'gnb': 'Packers', 'det': 'Lions', 'nor': 'Saints', 'car': 'Panthers', 'atl': 'Falcons', 'tam': 'Buccaneers', 'ram': 'Rams', 'stl': 'Rams', 'lar': 'Rams', 'sea': 'Seahawks', 'sfo': '49ers', 'crd': 'Cardinals', 'ari': 'Cardinals'}
    
    def multi_comparison(self, years):
        df = {}
        years = [str(year) for year in years]
        l = []
        for year in years:
            print(f'Year: {year}')
            df = self.comparison(year)
            df['Year'] = [int(year)]*len(df)
            l.append(df)
        return pd.concat(l, axis = 0, sort = False)
        
    def comparison(self, year):
        self.df = pd.concat([self.win_shares_roster(year), self.madden_roster(year)[['Overall']]], axis = 1, sort = False).dropna()
        # print(f'Correlation of AV with Madden Overall: {np.corrcoef(self.df.AV, self.df.Overall)}')
        
        for ws in [i for i in self.df.columns if 'WinShares' in i]: 
            print(f'Correlation of {ws} with Madden all Overalls: {round(np.corrcoef(self.df[ws], self.df.Overall)[0][1], 2)} 85+ Ovr: {round(np.corrcoef(self.df[self.df.Overall >= 85][ws], self.df[self.df.Overall >= 85].Overall)[0][1], 2)} AV: {round(np.corrcoef(self.df[ws], self.df.AV)[0][1], 2)}')
        return self.df
    
    def madden_roster(self, year):
        try:
            df = pd.read_csv(f'data/{year}madden.csv').set_index(['Player', 'MaddenTeam'])
        except FileNotFoundError:
            df = self._scrape_madden_roster(year)
            df.to_csv(f'data/{year}madden.csv')
        return df
            
    def _scrape_madden_roster(self, year):
        url = f'https://maddenratings.weebly.com/madden-nfl-{self.year_to_madden(year)}.html'
        ua = UserAgent()
        headers = {"User-Agent": ua.random}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'lxml')
        urls = [f'https://maddenratings.weebly.com{i["href"]}' for i in soup.findAll('a') if i.has_attr('href') and 'xlsx' in i['href']][:32]
        teams = [i[-1] for i in [i.get_text()[:-6].split() for i in soup.findAll('div') if i.has_attr('style') and i['style'] == "display:block;font-size:90%"][1:33]]
        df = pd.DataFrame({})
        for e, u in enumerate(urls):
            new = pd.read_excel(u)
            if 'Team' not in new.columns:
                new['Team'] = teams[e]
            if len(np.unique(new['Team'])[0].split()) > 1:
                new['Team'] = [i.split()[-1] for i in new['Team'].values]
            df = pd.concat([df, new], axis = 0, sort = False)
        # df = pd.DataFrame({})    
        # new = []
        # for u in urls:
            # new.append(pd.read_excel(u))
        # df = pd.concat([df, new], axis = 0, sort = False)
        if 'Name' not in df.columns:
            if 'LAST' in df.columns and 'FIRST' in df.columns:
                df['Name'] = [f'{i} {j}' for i, j in df[['FIRST', 'LAST']].values]
            if 'Last Name' in df.columns and 'First Name' in df.columns:
                df['Name'] = [f'{i} {j}' for i, j in df[['First Name', 'Last Name']].values]
            
        if 'Overall' not in df.columns:
            if 'OVR' in df.columns:
                df = df.rename(columns = {'OVR': 'Overall'})
            if 'OVERALL RATING' in df.columns:
                df = df.rename(columns = {'OVERALL RATING': 'Overall'})

        df = df.rename(columns = {'Team': 'MaddenTeam', 'Name': 'Player'}).set_index(['Player', 'MaddenTeam'])
        
        if not df.index.is_unique:
            df = df.reset_index().sort_values(by = 'Overall', ascending = False).drop_duplicates(subset = 'Player', keep = 'first').set_index(['Player', 'MaddenTeam'])
        
        return df

    def win_shares_roster(self, year):
        try:
            df = pd.read_csv(f'data/{year}winshares.csv')
        except FileNotFoundError:
            df = WinShares().win_shares(year)
            df.to_csv(f'data/{year}winshares.csv')
        df['MaddenTeam'] = [self.teams[tm] for tm in df['Team'].values]
        return df.groupby(['Player', 'MaddenTeam']).sum()

