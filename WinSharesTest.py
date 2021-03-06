import requests
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib.pyplot as plt
from fake_useragent import UserAgent
import numpy as np
import re
import os
import warnings

class WinShares:
    
    def __init__(self):
        self.teams = {'nwe': {'NE'}, 'mia': {'MIA'}, 'buf': {'BUF'}, 'nyj': {'NYJ'}, 'bal': {'BAL'}, 'rav': {'BAL'}, 'pit': {'PIT'}, 'cle': {'CLE'}, 'cin': {'CIN'}, 'hou': {'HOU'}, 'htx': {'HOU'}, 'clt': {'IND'}, 'ind': {'IND'}, 'oti': {'TEN'}, 'ten': {'TEN'}, 'jax': {'JAX', 'JAC'}, 'kan': {'KC'}, 'sdg': {'SD', 'LAC'}, 'lac': {'SD', 'LAC'}, 'den': {'DEN'}, 'rai': {'OAK'}, 'oak': {'OAK'}, 'dal': {'DAL'}, 'phi': {'PHI'}, 'was': {'WAS'}, 'nyg': {'NYG'}, 'chi': {'CHI'}, 'min': {'MIN'}, 'gnb': {'GB'}, 'det': {'DET'}, 'nor': {'NO'}, 'car': {'CAR'}, 'atl': {'ATL'}, 'tam': {'TB'}, 'ram': {'STL', 'LA'}, 'stl': {'STL', 'LA'}, 'lar': {'STL', 'LA'}, 'sea': {'SEA'}, 'sfo': {'SF'}, 'crd': {'ARI'}, 'ari': {'ARI'}}
        self.pbp = None
        self.games = None
    
    def win_shares(self, year):
        """calculate win shares"""
        if type(year) == int or type(year) == str:
            return self._ws(str(year))
        return pd.concat([self._ws(str(y)) for y in year], axis = 0, sort = False)
    
    def _ws(self, year):
        """calculates win shares for the given year"""
        pd.options.mode.chained_assignment = None
        warnings.filterwarnings('ignore')
        #create dictionary w team: wins
        standings = self._scrape_standings(year)
        teams = {i: round(j*16, 1) for i, j in standings.set_index('Tm').to_dict()['W-L%'].items()}            
        l = []
        for count, tm in enumerate(teams):
            print(f'{year} {tm} team # {count + 1} of 32', end = '\r')
            l.append(self.calculate_season_wpa(year, tm))
        df = pd.concat(l, axis = 0, sort = False)
        
        #adjusts TeamWPA to league average TeamWPA for year
        wpa_avg = {i: j for i, j in df.mean().to_dict().items() if i in ['TeamOffWPA', 'TeamDefWPA', 'TeamSTWPA']}
        for k in ['Off', 'Def', 'ST']:  df[f'TeamAdj{k}WPA'] = [w - wpa_avg[f'Team{k}WPA'] for w in df[f'Team{k}WPA'].values]

        l = []
        print('Computing WinShares...')
        for count, tm in enumerate(teams):
            for wk in np.unique(df[df.Team == tm]['Week']):
                temp = df[(df.Team == tm) & (df.Week == wk) & ((~np.isnan(df.TeamOffWPA)) | (~np.isnan(df.TeamDefWPA)) | (~np.isnan(df.TeamSTWPA)))]
                for k in ['Off', 'Def', 'ST']:
                    temp[f'{k}WPA'] = temp[[f'{k}RelImp']] * temp[[f'TeamAdj{k}WPA']].mode().values.item(0)
                    temp[f'{k}WPA'] = temp[f'{k}WPA'].apply(lambda x: x if x > 0 else 0)
                    
                    # temp[f'W{k}'] = (temp[f'{k}WPA'] / abs(temp[f'{k}WPA'].sum())).apply(lambda x: x if x > 0 else 0)
                    
                temp['TotWPA'] = temp[['OffWPA', 'DefWPA', 'STWPA']].sum(axis = 1)
                temp['TeamGameWPA'] = [temp['TotWPA'].sum(axis = 0)] * len(temp)
                temp['WinShares'] = (np.unique(temp.WinVal)[0] / abs(np.unique(temp.TeamGameWPA))) * temp[['TotWPA']]
                # temp['NewWinShares'] = np.unique(temp.WinVal)[0] / temp[['WOff', 'WDef', 'WST']].sum(axis = 1).sum(axis = 0) * temp[['WOff', 'WDef', 'WST']].sum(axis = 1)
                temp.fillna(0, inplace = True)
                l.append(temp)
        final = pd.concat(l, axis = 0, sort = False)    
        if 'Unnamed: 0' in final.columns:
            final.drop('Unnamed: 0', axis = 1, inplace = True)
        final['Year'] = [year]*len(final)
        return final

    def calculate_season_wpa(self, year, team):
        """creates df w roster info, snap count info, and relative importance for each player in year/team"""
        year, team = str(year), str(team)
        sched = self._scrape_schedule(year, team)
        sched = sched[sched.Week.isin([i for i in range(18)])]
        roster = self._scrape_roster(year, team)
        wpa = self._scrape_game_wpa(year, team)
        if type(wpa) == type(None):
            return
        l = []
        for wk in sched[['Week']].values:   
            boxscore = sched[sched.Week == wk[0]][['Boxscore']].values[0][0]
            win = sched[sched.Week == wk[0]][['Wins']].values[0][0]
            if not boxscore:
                continue
            snap_counts = self._scrape_boxscore(year, team, boxscore) 
            snap_counts['WinVal'] = [win]*len(snap_counts)
            #wpa_wk = wpa for given week, duplicated into len(snap_counts) rows 
            wpa_wk = pd.concat([wpa[wpa.week == wk[0]]]*len(snap_counts), ignore_index = True).set_index('week')
            snap_counts = pd.concat([snap_counts.set_index('Week'), wpa_wk], axis = 1, sort = False).reset_index().rename(columns = {'index': 'Week'})
            
            #snap_counts with wpa info concatenated to roster information by Player
            if not snap_counts.set_index('Player').index.is_unique:
                snap_counts['TotPct'] = snap_counts[['OffPct', 'DefPct', 'STPct']].sum(axis = 1)
                snap_counts = snap_counts.sort_values(by = 'TotPct', ascending = False).drop_duplicates(subset = 'Player', keep = 'first').set_index('Player').drop('TotPct', axis = 1).reset_index()
             
            if not roster.set_index('Player').index.is_unique:
                roster = roster.sort_values(by = 'AV', ascending = False).drop_duplicates(subset = 'Player', keep = 'first')
             
            new = pd.concat([snap_counts.set_index('Player'), roster.rename(columns = {'Pos': 'RosterPos'}).set_index('Player')], axis = 1, sort = False)
            new = self.calculate_relative_importance(new.reset_index().rename(columns = {'index': 'Player'}))   
            l.append(new)
        df = pd.concat(l, axis = 0, sort = False)
        df = df[~np.isnan(df.Week)]
        df['Team'] = [team]*len(df)
        return df   

    def calculate_relative_importance(self, df):
        """
        Calculates relative importance of a player to his team
        
        df: data frame of roster with snap counts for each player
        """
        l = [df]
        for k in ['Off', 'Def', 'ST']:
            temp = df[(df[f'{k}Pct'] != 0.0) & (~np.isnan(df[f'{k}Pct']))]
            bottom = sum([(av * pct) / sum(temp['AV']) for av, pct in temp[['AV', f'{k}Pct']].values])
            temp[f'{k}RelImp'] = [(av * pct) / (sum(temp['AV']) * bottom) for av, pct in temp[['AV', f'{k}Pct']].values]
            if k != 'ST':
                #offense/defense
                categories = [i for i in [f'{k}_pass', f'{k}_run', f'{k}_no_play', f'{k}_qb_kneel', f'{k}_qb_spike'] if i in temp.columns]
                wpa = np.unique(temp[categories].sum(axis = 1))[0]
                temp[f'Team{k}WPA'] = [float(wpa)]*len(temp)
            else:
                #special teams
                categories = [i for i in ['Def_extra_point', 'Def_field_goal', 'Def_kickoff', 'Def_punt', 'Off_extra_point', 'Off_field_goal', 'Off_kickoff', 'Off_punt'] if i in temp.columns]
                wpa = np.unique(temp[categories].sum(axis = 1))[0]
                temp[f'Team{k}WPA'] = [float(wpa)]*len(temp)
            l.append(temp[[f'{k}RelImp', f'Team{k}WPA']])
        df = pd.concat(l, axis = 1, sort = False)
        return df
        
    def _scrape_standings(self, year):
        """scrapes year standings from pfr"""
        year = str(year)
        url = f'https://www.pro-football-reference.com/years/{year}/'
        ua = UserAgent()
        headers = {'User-Agent': ua.random}
        response = requests.get(url, headers = headers)
        comm = re.compile("<!--|-->")
        soup = BeautifulSoup(comm.sub("", response.text), 'lxml')
        df = pd.DataFrame({})
        for conf in ['AFC', 'NFC']:
            table = soup.find('table', id = conf)
            col_names = [i.get_text() for i in table.find('thead').findAll('th')]
            row_data = [[self._floatify(i.get_text()) if i.find('a') == None else i.find('a')['href'][7:10] for i in row.findAll(['th', 'td'])] for row in table.find('tbody').findAll('tr') if not row.has_attr('class')]
            df = pd.concat([df, pd.DataFrame(row_data, columns = col_names)], axis = 0, sort = False)
        return df

    def _scrape_schedule(self, year, team):
        """scrapes schedule and links for each game from pfr"""
        year, team = str(year), str(team)
        url = f'https://www.pro-football-reference.com/teams/{team}/{year}.htm'
        ua = UserAgent()
        headers = {"User-Agent": ua.random}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'lxml')
        table = soup.find('table', id = 'games')
        thead = table.find('thead')
        tr = thead.findAll('tr')[-1]
        col_names = [i.get_text() for i in tr.findAll('th')]
        col_names[4] = 'Boxscore'
        col_names[5] = 'Wins'
        col_names[8] = 'At'
        tbody = table.find('tbody')
        tr = tbody.findAll('tr') 
        
        row_data = [[self._floatify(i.get_text()) if i.get_text() != 'boxscore' else i for i in row.findAll(['th', 'td'])] for row in tr]
        df = pd.DataFrame(row_data, columns = col_names)
        df['Boxscore'] = [i.findAll('a')[0].get('href') if type(i) != float else None for i in df['Boxscore'].values]
        df['Wins'] = [{'W': 1, 'L': 0, 'T': 0.5, '': None}[i] if i in ['W', 'L', 'T'] else None for i in df['Wins'].values]
        return df   
        
        
    def _scrape_roster(self, year, team):
        """scrapes pfr roster data"""
        year = str(year)
        team = str(team)
        url = f'https://www.pro-football-reference.com/teams/{team}/{year}_roster.htm'
        ua = UserAgent()
        headers = {'User-Agent': ua.random}
        response = requests.get(url, headers = headers)
        comm = re.compile("<!--|-->")
        soup = BeautifulSoup(comm.sub("", response.text), 'lxml')
        table = soup.find('table', id = 'games_played_team')
        col_names = [i.get_text().strip() for i in table.find('thead').find('tr').findAll('th')]
        row_data = [[self._floatify(i.get_text().replace('*', '').replace('+', '')) for i in row.findAll(['th', 'td'])] for row in table.find('tbody').findAll('tr') if not row.has_attr('class')]
        df = pd.DataFrame(row_data, columns = col_names)
        return df
        
        
    def _scrape_boxscore(self, year, team, gameid):
        """scrapes pfr boxscore and returns snap_counts for given year, team, and gameid"""
        year, team, gameid = str(year), str(team), str(gameid)
        url = f'https://www.pro-football-reference.com/{gameid}'
        ua = UserAgent()
        headers = {'User-Agent': ua.random}
        response = requests.get(url, headers=headers)
        comm = re.compile("<!--|-->")
        soup = BeautifulSoup(comm.sub("", response.text), 'lxml')
        # determine home and away team
        pfrroad, pfrhome = [i['href'] for i in soup.find('table', class_ = 'linescore nohover stats_table no_freeze').find('tbody').findAll('a') if 'teams' in i['href']]
        if team in pfrroad:
            id = 'vis_snap_counts'
        elif team in pfrhome:
            id = 'home_snap_counts'
        
        table = soup.find('table', id = id)
        col_names = ['Player', 'Pos', 'OffNum', 'OffPct', 'DefNum', 'DefPct', 'STNum', 'STPct']
        row_data = [[self._floatify(i.get_text()) for i in row.findAll(['th','td'])] for row in table.find('tbody').findAll('tr') if not row.has_attr('class')]
        snap_counts = pd.DataFrame(row_data, columns = col_names)
        
        #attach week of game to snap_counts df
        week = soup.find('div', id = 'div_other_scores').find('h2').find('a').get_text()
        snap_counts['Week'] = [int(week[(week.index(' ') + 1):])]*(len(snap_counts))
        
        return snap_counts
        
    def _scrape_game_wpa(self, year, team):
        """scrape wpa from nflscrapR for given year and team"""
        year, team = str(year), str(team)
        #load data only if unloaded
        if type(self.pbp) != pd.core.frame.DataFrame and type(self.games) != pd.core.frame.DataFrame:
            self._load_win_probability(year)
        pd.options.mode.chained_assignment = None
        
        team, df = str(team), self.pbp
        team = [i for i in self.teams[team] if i in np.unique(df[['home_team', 'away_team']])][0]
        df = df[(df.home_team == team) | (df.away_team == team)]

        #creates dataframe with week as index and playclass (Off_run, Def_pass, etc.) as columns. Values are cumulative WPA for week and playclass
        try:
            df[f'{team}_wpa'] = [i if j == team else -i for i, j in df[['wpa', 'posteam']].values]
            df = pd.concat([df.set_index('game_id'), self.games[(self.games.home_team == team) | (self.games.away_team == team)].set_index('game_id')[['week']]], axis = 1, sort = False).reset_index()
            df['playclass'] = [f'Off_{j}' if i == team else f'Def_{j}' for i, j in df[['posteam', 'play_type']].values]
            df = df.groupby(['week', 'playclass']).sum().reset_index().pivot_table(values = f'{team}_wpa', columns = 'playclass', index = 'week').reset_index()
        except:
            print(f'Unable to scrape WPA for {year} {team}')
            return
        return df
        
    def _load_win_probability(self, year):
        """loads play-by-play data and game data from nflscrapR"""
        year = str(year)
        self.pbp = pd.read_csv(f'https://raw.githubusercontent.com/ryurko/nflscrapR-data/master/play_by_play_data/regular_season/reg_pbp_{year}.csv', low_memory = False)
        self.games = pd.read_csv(f'https://raw.githubusercontent.com/ryurko/nflscrapR-data/master/games_data/regular_season/reg_games_{year}.csv', low_memory = False)
  
    def _floatify(self, obj):
        """turns objects into floats and handles percents and empty cells"""
        if type(obj) == float:
            return obj
        if obj == '':
            obj = np.NaN
            return obj
        try:
            if '%' in obj:
                obj = float(obj[:-1])/100
        except:
            pass
        try:
            obj = float(obj)
            return obj
        except:
            return obj  

# import time
# start = time.time()
# W = WinShares()
# df = W.win_shares('2017')
# end = time.time()
# print(end - start)
# # snap_counts = S._scrape_boxscore(year, team, boxscore)

# # sched = S._scrape_schedule(year, team)

# import time
# start = time.time()
# df = W.win_shares(year)
# # df.to_csv('2018winshares.csv')
# # test = S.calculate_season_wpa('2018', 'kan')
# # df = pd.read_csv('test2018winshares.csv')
# end = time.time()
# print(end - start)
# # df.to_csv(f'test2018winshares.csv')
# # print({i: {''} for i in S.teams})
# # # roster = S._scrape_roster(year, team).set_index('Player')
# start = time.time()
# # df = S.calculate_season_wpa(year, team)
# # A = Analysis(year)
# # df = A.df
# end = time.time()
# print(end - start)
# # o, d = S._scrape_season_expected_points(year, team)
# # print(o, d)
# # # print(df)           