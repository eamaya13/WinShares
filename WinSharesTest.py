import requests
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib.pyplot as plt
from fake_useragent import UserAgent
import numpy as np
import re
import os

# df = pd.read_pickle('nfl-pbp.pkl')

# df = pd.read_csv('nfl-pbp-2009-2018.csv')

class WinProbability:
    
    def __init__(self, year):
        self.year = str(year)
        self.pbp = pd.read_csv(os.path.join(os.getcwd(), '..', f'nflscrapR-data/play_by_play_data/regular_season/reg_pbp_{self.year}.csv' ), low_memory = False)
        self.games = pd.read_csv(os.path.join(os.getcwd(), '..', f'nflscrapR-data/games_data/regular_season/reg_games_{self.year}.csv'), low_memory = False)
        # self.df = pd.concat([self.pbp.set_index('game_id'), self.games.set_index('game_id')[['week']]], axis = 1, sort = False).reset_index()
        self.teams = {'nwe': {'NE'}, 'mia': {'MIA'}, 'buf': {'BUF'}, 'nyj': {'NYJ'}, 'bal': {'BAL'}, 'rav': {'BAL'}, 'pit': {'PIT'}, 'cle': {'CLE'}, 'cin': {'CIN'}, 'hou': {'HOU'}, 'htx': {'HOU'}, 'clt': {'IND'}, 'ind': {'IND'}, 'oti': {'TEN'}, 'ten': {'TEN'}, 'jax': {'JAX', 'JAC'}, 'kan': {'KC'}, 'sdg': {'SD', 'LAC'}, 'lac': {'SD', 'LAC'}, 'den': {'DEN'}, 'rai': {'OAK'}, 'oak': {'OAK'}, 'dal': {'DAL'}, 'phi': {'PHI'}, 'was': {'WAS'}, 'nyg': {'NYG'}, 'chi': {'CHI'}, 'min': {'MIN'}, 'gnb': {'GB'}, 'det': {'DET'}, 'nor': {'NO'}, 'car': {'CAR'}, 'atl': {'ATL'}, 'tam': {'TB'}, 'ram': {'STL', 'LA'}, 'stl': {'STL', 'LA'}, 'lar': {'STL', 'LA'}, 'sea': {'SEA'}, 'sfo': {'SF'}, 'crd': {'ARI'}, 'ari': {'ARI'}}

    def scrape_game_wpa(self, team):  
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
        
# E = ExpectedPoints(2018)
# df = E.scrape_game_wpa('nwe')

class SeasonWinShares:
    
    def __init__(self, year):
        self.teams = {'nwe': 'Patriots', 'mia': 'Dolphins', 'buf': 'Bills', 'nyj': 'Jets', 'bal': 'Ravens', 'rav': 'Ravens', 'pit': 'Steelers', 'cle': 'Browns', 'cin': 'Bengals', 'hou': 'Texans', 'htx': 'Texans', 'clt': 'Colts', 'ind': 'Colts','oti': 'Titans', 'ten': 'Titans', 'jax': 'Jaguars', 'kan': 'Chiefs', 'sdg': 'Chargers', 'lac': 'Chargers', 'den': 'Broncos', 'rai': 'Raiders', 'oak': 'Raiders', 'dal': 'Cowboys', 'phi': 'Eagles', 'was': 'Redskins', 'nyg': 'Giants', 'chi': 'Bears', 'min': 'Vikings', 'gnb': 'Packers', 'det': 'Lions', 'nor': 'Saints', 'car': 'Panthers', 'atl': 'Falcons', 'tam': 'Buccaneers', 'ram': 'Rams', 'stl': 'Rams', 'lar': 'Rams', 'sea': 'Seahawks', 'sfo': '49ers', 'crd': 'Cardinals', 'ari': 'Cardinals'}
        self.year = str(year)
        self.W = None
        self.roster = None
    
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
            
    def _calculate_relative_importance(self, df):
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
                wpa = np.unique(temp[[f'{k}_pass', f'{k}_run', f'{k}_no_play', f'{k}_qb_kneel', f'{k}_qb_spike']].sum(axis = 1))[0]
                # rel = temp[f'{k}RelImp'] if wpa >= 0 else temp[f'{k}InvRelImp']
                rel = temp[f'{k}RelImp']
                # temp[f'{k}WPA']
                temp[f'Team{k}WPA'] = [float(wpa)]*len(temp)
                # temp[f'{k}WPA'] = wpa*np.array(rel)
            else: 
                #fix this for ST, fg should be kicker and punt should punter all that
                wpa = np.unique(temp[['Def_extra_point', 'Def_field_goal', 'Def_kickoff', 'Def_punt', 'Off_extra_point', 'Off_field_goal', 'Off_kickoff', 'Off_punt']].sum(axis = 1))[0]
                # rel = temp[f'{k}RelImp'] if wpa >= 0 else temp[f'{k}InvRelImp']
                rel = temp[f'{k}RelImp']
                temp[f'Team{k}WPA'] = [float(wpa)]*len(temp)
                # temp[f'{k}WPA'] = wpa*np.array(rel)
            df = pd.concat([df, temp[[f'{k}RelImp', f'Team{k}WPA']]], sort = False, axis = 1)
        return df
    
    def calculate_season_wpa(self, year, team):
        year, team = str(year), str(team)
        sched = self._scrape_schedule(year, team)
        sched = sched[sched.Week.isin([i for i in range(18)])]
        roster = self._scrape_roster(year, team)
        self.W = self.W if self.W != None else WinProbability(year)
        wpa = self.W.scrape_game_wpa(team).reset_index()
        df = pd.DataFrame({})
        #calculate relative importance and teamwpa for 
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
            new = self._calculate_relative_importance(new.reset_index().rename(columns = {'index': 'Player'}))            
            df = pd.concat([df, new], sort = False, axis = 0)
        
        df = df[~np.isnan(df.Week)]
        df['Team'] = [team]*len(df)
        return df
            
    def _scrape_yearly_snap_counts(self, year, team):
        year = str(year)
        team = str(team)
        url = f'https://www.pro-football-reference.com/teams/{team}/{year}-snap-counts.htm'
        ua = UserAgent()
        headers = {'User-Agent': ua.random}
        response = requests.get(url, headers = headers)
        soup = BeautifulSoup(response.text, 'lxml')
        table = soup.find('table', id = 'snap_counts')
        col_names = [i.get_text() for i in table.find('thead').findAll('tr')[-1].findAll('th')]
        col_names = ['Player', 'Pos', 'OffNum', 'OffPct', 'DefNum', 'DefPct', 'STNum', 'STPct', '']
        row_data = [[self._floatify(i.get_text()) for i in row.findAll(['th','td'])] for row in table.find('tbody').findAll('tr') if not row.has_attr('class')]
        df = pd.DataFrame(row_data, columns = col_names)
        return df
         
    # def _scrape_season_expected_points(self, year, team):
        # sched = self._scrape_schedule(year, team)
        # offep = sched[sched.Week.isin([i for i in range(18)])].sum()['Offense']
        # defep = sched[sched.Week.isin([i for i in range(18)])].sum()['Defense']
        # return offep, defep
    
    def _scrape_schedule(self, year, team):
        year = str(year)
        team = str(team)
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
        
    def _scrape_boxscore(self, year, team, gameid):
        year, team, gameid = str(year), str(team), str(gameid)
        url = f'https://www.pro-football-reference.com/{gameid}'
        ua = UserAgent()
        headers = {'User-Agent': ua.random}
        response = requests.get(url, headers=headers)
        comm = re.compile("<!--|-->")
        soup = BeautifulSoup(comm.sub("", response.text), 'lxml')
        table = soup.find('table', id = 'expected_points')
        col_names = ['Tm', 'Total', 'OffTotal', 'OffPass', 'OffRush', 'OffTOvr', 'DefTotal', 'DefPass', 'DefRush', 'DefTOvr', 'STTotal', 'KO', 'KR', 'P', 'PR', 'FG/XP']
        row_data = [[self._floatify(i.get_text()) for i in row.findAll(['th', 'td'])] for row in table.find('tbody').findAll('tr')]
        # expected_points = pd.DataFrame(row_data, columns = col_names)
        
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
        
    def win_shares(self, year):
        standings = self._scrape_standings(year)
        teams = {i: round(j*16, 1) for i, j in standings.set_index('Tm').to_dict()['W-L%'].items()}
        pd.options.mode.chained_assignment = None
        df = pd.DataFrame({})
        # for count, tm in enumerate(teams):
            # # print(f'team: {tm}')
            # print(f'team # {count + 1} of 32', end = '\r')
            # new = self.calculate_season_wpa(year, tm)
            # df = pd.concat([df, new], axis = 0, sort = False)
        
        # df = pd.read_csv('test2018winshares.csv')
        
        # df.to_csv('middletest.csv')
        df = pd.read_csv('middletest.csv')
        
        wpa_avg = {i: j for i, j in df.mean().to_dict().items() if i in ['TeamOffWPA', 'TeamDefWPA', 'TeamSTWPA']}
        pos_avg = {f'{k}RelImp': df.groupby('Pos').mean()[[f'{k}RelImp']].to_dict()[f'{k}RelImp'] for k in ['Off', 'Def', 'ST']}
        # for k in ['Off', 'Def', 'ST']:  df[f'TeamAdj{k}WPA'] = [w - wpa_avg[f'Team{k}WPA'] for w in df[f'Team{k}WPA'].values]
        
        # df.drop('Unnamed: 0', axis = 1, inplace = True)
        # for k in ['Off', 'Def', 'ST']:  df[f'Adj{k}RelImp'] = [rel - pos_avg[f'{k}RelImp'][pos] for pos, rel in df[['Pos', f'{k}RelImp']].values]
        
        
        final = pd.DataFrame({})
        for count, tm in enumerate(teams):
            print(f'team {count + 1}', end = '\r')
            new = pd.DataFrame({})
            for wk in np.unique(df[df.Team == tm]['Week']):
                temp = df[(df.Team == tm) & (df.Week == wk) & ((~np.isnan(df.TeamOffWPA)) | (~np.isnan(df.TeamDefWPA)) | (~np.isnan(df.TeamSTWPA)))]
                for k in ['Off', 'Def', 'ST']:
                    # X = temp.mean()[[f'TeamAdj{k}WPA']][0]/temp.sum()[[f'Adj{k}RelImp']][0]
                    # temp[f'Adj{k}WPA'] = temp[[f'Adj{k}RelImp']] * abs(X)
                    bottom = .01 if abs(temp.sum()[[f'{k}RelImp']][0]) < 0.01 else temp.sum()[[f'{k}RelImp']][0]
                    # X = (temp.mean()[[f'TeamAdj{k}WPA']][0])/bottom
                    X = (temp.mean()[[f'Team{k}WPA']][0])/bottom
                    # temp[f'Adj{k}WPA'] = temp[[f'{k}RelImp']] * abs(X)
                    temp[f'{k}WPA'] = temp[[f'{k}RelImp']] * X
                temp['TotWPA'] = temp[['OffWPA', 'DefWPA', 'STWPA']].sum(axis = 1)
                temp['TeamGameWPA'] = [temp['TotWPA'].sum(axis = 0)] * len(temp) if abs(temp['TotWPA'].sum(axis = 0)) > 0.1 else 0.1 * (temp['TotWPA'].sum(axis = 0) / abs(temp['TotWPA'].sum(axis = 0)))
                temp['WinShares'] = (np.unique(temp.WinVal)[0] / np.unique(temp.TeamGameWPA)) * temp[['TotWPA']]
                new = pd.concat([new, temp], axis = 0, sort = False)
            # new['TotAdjWPA'] = new[['AdjOffWPA', 'AdjDefWPA', 'AdjSTWPA']].sum(axis = 1) 
            # new['TeamTotAdjWPA'] = [new['TotAdjWPA'].sum(axis = 0)]*len(new)
            # new['TotWPA'] = new[['OffWPA', 'DefWPA', 'STWPA']].sum(axis = 1) 
            # new['TeamTotWPA'] = [new['TotWPA'].sum(axis = 0)]*len(new)
            final = pd.concat([final, new], axis = 0, sort = False)
            
        if 'Unnamed: 0' in final.columns:
            final.drop('Unnamed: 0', axis = 1, inplace = True)
        # final['TotAdjWPA'] = final[['AdjOffWPA', 'AdjDefWPA', 'AdjSTWPA']].sum(axis = 1)  
        #todo fix this
        # final['WinShares'] = [wpa*(teams[tm]/totwpa) for wpa, tm, totwpa in final[['TotWPA', 'Team', 'TeamTotWPA']].values]        
        return final
    # def calculate_game_ep(self, year, team, gameid):   
        # year, team, gameid = str(year), str(team), str(gameid)
        # snap_counts = S._scrape_boxscore(year, team, gameid)
        # self.E = self.E if self.E != None else ExpectedPoints(year)
        # expected_points = self.wpa if self.wpa != None else self.E.scrape_game_wpa(team)
        # roster = self.roster if self.roster != None else S._scrape_roster(year, team)
        # new = pd.concat([snap_counts.set_index('Player'), roster.rename(columns = {'Pos': 'RosterPosition'}).set_index('Player')], sort = False, axis = 1)
        
        # pd.options.mode.chained_assignment = None
        # for k in ['Off', 'Def', 'ST']:
            # ep = expected_points[f'{k}Total'].values[0]
            # temp = new[(new[f'{k}Pct'] != 0.0) & (~np.isnan(new[f'{k}Pct']))]
            # bottom = sum([(i * j) / sum(temp['AV']) for i, j in temp[['AV', f'{k}Pct']].values])
            # temp[f'{k}RelImp'] = [(i * j / sum(temp['AV']))/bottom for i, j in temp[['AV', f'{k}Pct']].values]
            # temp[f'{k}EP'] = ep*np.array(temp[f'{k}RelImp'])
            # new = pd.concat([new, temp[[f'{k}RelImp', f'{k}EP']]], sort = False, axis = 1)
            
        # return new
  
class Analysis:
    
    def __init__(self, year, df = None):
        self.year = str(year)
        try:
            print(f'Reading from csv...')
            data = pd.read_csv(f'{self.year}winshares.csv')
            data.drop(columns = 'Unnamed: 0', inplace = True)
        except FileNotFoundError:
            print(f'File not found: reading from input...')
            data = df if df != None else None
            if data == None: 
                print(f'Scraping data...')
                S = SeasonWinShares(year)
                data = S.win_shares(year)
                data.to_csv(f'{self.year}winshares.csv')
        self.df = data
        
    def adjust_by_team(self):
        df = self.df.copy(True)
        df = df[((~np.isnan(df.OffWPA)) & (df.OffWPA != 0.0)) | ((~np.isnan(df.DefWPA)) & (df.DefWPA != 0.0)) | ((~np.isnan(df.STWPA)) & (df.STWPA != 0.0))]
        for k in ['Off', 'Def', 'ST']:
            
        
            team_wpa = df[(~np.isnan(df[f'{k}WPA'])) & (df[f'{k}WPA'] != 0.0)].groupby('Team').mean().to_dict()[f'{k}WPA']
            # df[f'TeamAdj{k}WPA'] = [(wpa - team_wpa[tm]) for tm, wpa in df[['Team', f'{k}WPA']].values]#does this need to be divided?
            
            pos_wpa = df[(~np.isnan(df[f'{k}WPA'])) & (df[f'{k}WPA'] != 0.0)].groupby('Pos').mean().to_dict()[f'{k}WPA']
            # df[f'PosAdj{k}WPA'] = [(wpa - pos_wpa[pos]) if pos in pos_wpa else None for pos, wpa in df[['Pos', f'{k}WPA']].values]

            # df[f'FullAdj{k}WPA'] = [(wpa - team_wpa[tm]) for tm, wpa in df[['Team', f'PosAdj{k}WPA']].values]
            
            df[f'{k}AvgPos'] = [pos_wpa[pos] if pos in pos_wpa else None for pos in df['Pos'].values]
            df[f'{k}AvgTeam'] = [team_wpa[tm] for tm in df['Team'].values]
            df[f'{k}AdjVal'] = df[[f'{k}AvgPos', f'{k}AvgTeam']].sum(axis = 1)
            df[f'Adj{k}WPA'] = [wpa - avg if not np.isnan(wpa) else None for wpa, avg in df[[f'{k}WPA', f'{k}AdjVal']].values]
            # df[f'Adj{k}WPA'] = df[[f'{k}AdjVal', f'{k}WPA']].diff(axis = 1)
        df[f'TotWPA'] = df[['AdjOffWPA', 'AdjDefWPA', 'AdjSTWPA']].sum(axis = 1)
        
        return df
        
    
        
year, team, boxscore = '2018', 'nwe', '/boxscores/201810290buf.htm'

S = SeasonWinShares(year)
# snap_counts = S._scrape_boxscore(year, team, boxscore)

# sched = S._scrape_schedule(year, team)

import time
start = time.time()
df = S.win_shares(year)
df.to_csv('test2018winshares.csv')
end = time.time()
print(end - start)
# df.to_csv(f'test2018winshares.csv')
# print({i: {''} for i in S.teams})
# # roster = S._scrape_roster(year, team).set_index('Player')
start = time.time()
# df = S.calculate_season_wpa(year, team)
# A = Analysis(year)
# df = A.df
end = time.time()
print(end - start)
# o, d = S._scrape_season_expected_points(year, team)
# print(o, d)
# # print(df)           