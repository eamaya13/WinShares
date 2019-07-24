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
        """calculates win shares for the given year"""
        pd.options.mode.chained_assignment = None
        warnings.filterwarnings('ignore')
        #create dictionary w team: wins
        standings = self._scrape_standings(year)
        teams = {i: round(j*16, 1) for i, j in standings.set_index('Tm').to_dict()['W-L%'].items()}
        
        df = pd.DataFrame({})
        for count, tm in enumerate(teams):
            print(f'team # {count + 1} of 32', end = '\r')
            new = self.calculate_season_wpa(year, tm)
            df = pd.concat([df, new], axis = 0, sort = False)
        
        #adjusts TeamWPA to league average TeamWPA for year
        wpa_avg = {i: j for i, j in df.mean().to_dict().items() if i in ['TeamOffWPA', 'TeamDefWPA', 'TeamSTWPA']}
        for k in ['Off', 'Def', 'ST']:  df[f'TeamAdj{k}WPA'] = [w - wpa_avg[f'Team{k}WPA'] for w in df[f'Team{k}WPA'].values]
        
        # df.to_csv('middle.csv')
        # df = pd.read_csv('middle.csv')
        
        final = pd.DataFrame({})
        print('Computing WinShares...')
        for count, tm in enumerate(teams):
            # print(f'team {count + 1}', end = '\r')
            new = pd.DataFrame({})
            for wk in np.unique(df[df.Team == tm]['Week']):
                temp = df[(df.Team == tm) & (df.Week == wk) & ((~np.isnan(df.TeamOffWPA)) | (~np.isnan(df.TeamDefWPA)) | (~np.isnan(df.TeamSTWPA)))]
                for k in ['Off', 'Def', 'ST']:
                    bottom = temp.sum()[[f'{k}RelImp']][0] if abs(temp.sum()[[f'{k}RelImp']][0]) > 0.01 else .01 * temp.sum()[[f'{k}RelImp']][0]/abs(temp.sum()[[f'{k}RelImp']][0])
                    X = (temp.mean()[[f'TeamAdj{k}WPA']][0])/bottom
                    temp[f'{k}WPA'] = temp[[f'{k}RelImp']] * X
                    
                    temp[f'W{k}'] = (temp[f'{k}WPA'] / abs(temp[f'{k}WPA'].sum())).apply(lambda x: x if x > 0 else 0)
                    
                temp['TotWPA'] = temp[['OffWPA', 'DefWPA', 'STWPA']].sum(axis = 1)
                temp['TeamGameWPA'] = [temp['TotWPA'].sum(axis = 0)] * len(temp) if abs(temp['TotWPA'].sum(axis = 0)) > .3 else .3 * (temp['TotWPA'].sum(axis = 0) / abs(temp['TotWPA'].sum(axis = 0)))
                temp['OldWinShares'] = (np.unique(temp.WinVal)[0] / abs(np.unique(temp.TeamGameWPA))) * temp[['TotWPA']]
                temp['NewWinShares'] = np.unique(temp.WinVal)[0] / temp[['WOff', 'WDef', 'WST']].sum(axis = 1).sum(axis = 0) * temp[['WOff', 'WDef', 'WST']].sum(axis = 1)
                temp.NewWinShares.fillna(0, inplace = True)
                new = pd.concat([new, temp], axis = 0, sort = False)
            final = pd.concat([final, new], axis = 0, sort = False)
            
        if 'Unnamed: 0' in final.columns:
            final.drop('Unnamed: 0', axis = 1, inplace = True)

        return final

    def calculate_season_wpa(self, year, team):
        year, team = str(year), str(team)
        sched = self._scrape_schedule(year, team)
        sched = sched[sched.Week.isin([i for i in range(18)])]
        roster = self._scrape_roster(year, team)
        wpa = self._scrape_game_wpa(year, team).reset_index()
        df = pd.DataFrame({})
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
            new = pd.concat([snap_counts.set_index('Player'), roster.rename(columns = {'Pos': 'RosterPos'}).set_index('Player')], axis = 1, sort = False)
            new = self.calculate_relative_importance(new.reset_index().rename(columns = {'index': 'Player'}))            
            df = pd.concat([df, new], sort = False, axis = 0)
        
        df = df[~np.isnan(df.Week)]
        df['Team'] = [team]*len(df)
        return df   

    def calculate_relative_importance(self, df):
        #TODO calculate relative importance and also WPA per player, maybe find a way to do it while building the dataset that is also modular and ready for adjustment
        #also dont forget to experiment with rushing and passing splits
        for k in ['Off', 'Def', 'ST']:
            temp = df[(df[f'{k}Pct'] != 0.0) & (~np.isnan(df[f'{k}Pct']))]
            bottom = sum([(i * j) / sum(temp['AV']) for i, j in temp[['AV', f'{k}Pct']].values])
            temp[f'{k}RelImp'] = [(i * j / sum(temp['AV']))/bottom for i, j in temp[['AV', f'{k}Pct']].values]
            # temp[f'{k}InvRelImp'] = max(temp[f'{k}RelImp']) - temp[f'{k}RelImp']
            # temp[f'{k}Rank'] = temp[f'{k}RelImp'].rank(ascending = False)
            # temp[f'{k}InvRank'] = max(temp[f'{k}Rank']) - temp[f'{k}Rank']
            if k != 'ST':
                categories = [i for i in [f'{k}_pass', f'{k}_run', f'{k}_no_play', f'{k}_qb_kneel', f'{k}_qb_spike'] if i in temp.columns]
                wpa = np.unique(temp[categories].sum(axis = 1))[0]
                # rel = temp[f'{k}RelImp'] if wpa >= 0 else temp[f'{k}InvRelImp']
                rel = temp[f'{k}RelImp']
                # temp[f'{k}WPA']
                temp[f'Team{k}WPA'] = [float(wpa)]*len(temp)
                # temp[f'{k}WPA'] = wpa*np.array(rel)
            else: 
                #fix this for ST, fg should be kicker and punt should punter all that
                categories = [i for i in ['Def_extra_point', 'Def_field_goal', 'Def_kickoff', 'Def_punt', 'Off_extra_point', 'Off_field_goal', 'Off_kickoff', 'Off_punt'] if i in temp.columns]
                wpa = np.unique(temp[categories].sum(axis = 1))[0]
                # rel = temp[f'{k}RelImp'] if wpa >= 0 else temp[f'{k}InvRelImp']
                rel = temp[f'{k}RelImp']
                temp[f'Team{k}WPA'] = [float(wpa)]*len(temp)
                # temp[f'{k}WPA'] = wpa*np.array(rel)
            df = pd.concat([df, temp[[f'{k}RelImp', f'Team{k}WPA']]], sort = False, axis = 1)
        return df
        
    def _scrape_standings(self, year):
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
        # df['Wins'] = [{'W': 1, 'T': 0.5, 'L': 0, '': None}[i] if i == type(str) else None for i in df['Wins'].values]
        df['Wins'] = [{'W': 1, 'L': 0, 'T': 0.5, '': None}[i] if i in ['W', 'L', 'T'] else None for i in df['Wins'].values]
        return df   
        
        
    def _scrape_roster(self, year, team):
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
        year, team, gameid = str(year), str(team), str(gameid)
        url = f'https://www.pro-football-reference.com/{gameid}'
        ua = UserAgent()
        headers = {'User-Agent': ua.random}
        response = requests.get(url, headers=headers)
        comm = re.compile("<!--|-->")
        soup = BeautifulSoup(comm.sub("", response.text), 'lxml')
        # determine_home_away
        road, home = [i.get_text() for i in soup.find('table', id = 'scoring').find('thead').findAll('th') if i['data-stat'] in {'vis_team_score', 'home_team_score'}]
        pfrroad, pfrhome = [i['href'] for i in soup.find('table', class_ = 'linescore nohover stats_table no_freeze').find('tbody').findAll('a') if 'teams' in i['href']]
        if team in pfrroad:
            id = 'vis_snap_counts'
            # expected_points = expected_points.iloc[:1]
        elif team in pfrhome:
            id = 'home_snap_counts'
            # expected_points = expected_points.iloc[1:]
        
        table = soup.find('table', id = id)
        col_names = ['Player', 'Pos', 'OffNum', 'OffPct', 'DefNum', 'DefPct', 'STNum', 'STPct']
        row_data = [[self._floatify(i.get_text()) for i in row.findAll(['th','td'])] for row in table.find('tbody').findAll('tr') if not row.has_attr('class')]
        snap_counts = pd.DataFrame(row_data, columns = col_names)
        week = soup.find('div', id = 'div_other_scores').find('h2').find('a').get_text()
        snap_counts['Week'] = [int(week[(week.index(' ') + 1):])]*(len(snap_counts))
        return snap_counts
        # return expected_points, snap_counts
        
    def _scrape_game_wpa(self, year, team):  
        year, team = str(year), str(team)
        if type(self.pbp) != pd.core.frame.DataFrame and type(self.games) != pd.core.frame.DataFrame:
            self._load_win_probability(year)
        pd.options.mode.chained_assignment = None
        team, df = str(team), self.pbp
        team = [i for i in self.teams[team] if i in np.unique(df[['home_team', 'away_team']])][0]
        df = df[(df.home_team == team) | (df.away_team == team)]
        
        df[f'{team}_wpa'] = [i if j == team else -i for i, j in df[['wpa', 'posteam']].values]
        df = pd.concat([df.set_index('game_id'), self.games[(self.games.home_team == team) | (self.games.away_team == team)].set_index('game_id')[['week']]], axis = 1, sort = False).reset_index()
        #TODO find out which ep to use and create a smasher that creates a similar table as previously or one that is the whole year w weeks and redo the calculation for ep below
        df['playclass'] = [f'Off_{j}' if i == team else f'Def_{j}' for i, j in df[['posteam', 'play_type']].values]
        df = df.groupby(['week', 'playclass']).sum().reset_index().pivot_table(values = f'{team}_wpa', columns = 'playclass', index = 'week')
        return df

    def _load_win_probability(self, year):
        year = str(year)
        self.pbp = pd.read_csv(f'https://raw.githubusercontent.com/ryurko/nflscrapR-data/master/play_by_play_data/regular_season/reg_pbp_{year}.csv', low_memory = False)
        self.games = pd.read_csv(f'https://raw.githubusercontent.com/ryurko/nflscrapR-data/master/games_data/regular_season/reg_games_{year}.csv', low_memory = False)
  
    def _floatify(self, obj):
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

import time
start = time.time()
W = WinShares()
df = W.win_shares('2018')
end = time.time()
print(end - start)
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