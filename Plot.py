import numpy as np
import pandas as pd
import seaborn as sns; sns.set()
import matplotlib.pyplot as plt
import plotly.graph_objects as go

df_2014 = pd.read_csv('data/2014winshares.csv')
df_2015 = pd.read_csv('data/2015winshares.csv')
df_2016 = pd.read_csv('data/2016winshares.csv')
df_2017 = pd.read_csv('data/2017winshares.csv')
df_2018 = pd.read_csv('data/2018winshares.csv')

df = pd.concat([df_2014, df_2015, df_2016, df_2017, df_2018], axis = 0, sort = False)
df.Salary = [int(i.strip('$').replace(',','')) if type(i) != float else 0 for i in df.Salary]
pos_switch = {"NT": "DT", "FS": "S", "DB": "S", "SS":"S", 'T': "OL", 'G': "OL", "C": "OL"}
phase_switch = {"OL": "Off", "QB": "Off", 'WR':"Off", 'RB':"Off", 'TE':"Off", 'FB':"Off", 'LB':"Def", 'S':"Def", 'DE':"Def", 'CB':"Def", 'DT':"Def",  'P': "ST", 'K': "ST", 'LS':"ST"}
df['GroupPos'] = np.array([pos_switch[i] if i in pos_switch else i for i in df.Pos])
df['Phase'] = np.array([phase_switch[i] for i in df.GroupPos])

playoff_teams = [(2015, 'nwe'),
 (2015, 'pit'),
 (2015, 'cin'),
 (2015, 'htx'),
 (2015, 'den'),
 (2015, 'kan'),
 (2015, 'was'),
 (2015, 'gnb'),
 (2015, 'min'),
 (2015, 'car'),
 (2015, 'sea'),
 (2015, 'crd')] + [(2016, 'nwe'),
 (2016, 'mia'),
 (2016, 'pit'),
 (2016, 'htx'),
 (2016, 'kan'),
 (2016, 'rai'),
 (2016, 'dal'),
 (2016, 'nyg'),
 (2016, 'gnb'),
 (2016, 'det'),
 (2016, 'atl'),
 (2016, 'sea')]+ [(2017, 'nwe'),
 (2017, 'buf'),
 (2017, 'pit'),
 (2017, 'jax'),
 (2017, 'oti'),
 (2017, 'kan'),
 (2017, 'phi'),
 (2017, 'min'),
 (2017, 'car'),
 (2017, 'nor'),
 (2017, 'atl'),
 (2017, 'ram')]+ [(2018, 'nwe'),
 (2018, 'rav'),
 (2018, 'clt'),
 (2018, 'htx'),
 (2018, 'sdg'),
 (2018, 'kan'),
 (2018, 'dal'),
 (2018, 'phi'),
 (2018, 'chi'),
 (2018, 'nor'),
 (2018, 'sea'),
 (2018, 'ram')]
df["Playoff"] = np.array([True if (i, j) in playoff_teams else False for i, j  in df[['Year', 'Team']].values])

fig, ax = plt.subplots(1,2, figsize =(15, 5))
ax_1, ax_2 = ax
ax_1.set(xlim=(0, 8*(10**6)), ylim=(0,0.05)); ax_2.set(xlim=(0, 8*(10**6)), ylim=(0,0.05))

# ax_1.set(xlim=(0, 8*(10**6)), ylim=(0,0.09)); ax_2.set(xlim=(0, 8*(10**6)), ylim=(0,0.09))

sns.set_context('paper')

sns.regplot(x = 'Salary', y = 'WinShares', scatter = False,data = df[(df.Year.isin([2015, 2016, 2017, 2018]))].groupby(['GroupPos']).mean().reset_index(),  ax = ax_1, color = 'gray', ci = None)
sns.regplot(x = 'Salary', y = 'WinShares', scatter = False,data = df[(df.Year.isin([2015, 2016, 2017, 2018]))].groupby(['GroupPos']).mean().reset_index(),  ax = ax_2, color = 'gray', ci = None)

sns.scatterplot(x = 'Salary', y='WinShares', marker = 'o', hue = 'GroupPos', data= df[(df.Playoff == True) & (df.Phase == 'Off') & (df.Year.isin([2015, 2016, 2017, 2018]))].groupby(['GroupPos']).mean().reset_index() ,s = 100, ax = ax_1)
sns.scatterplot(x = 'Salary', y='WinShares', marker = 'X',hue = 'GroupPos', data= df[(df.Playoff == True) & (df.Phase == 'Def') & (df.Year.isin([2015, 2016, 2017, 2018]))].groupby(['GroupPos']).mean().reset_index() ,s = 100, ax = ax_1)
sns.scatterplot(x = 'Salary', y='WinShares', marker = 's',hue = 'GroupPos', data= df[(df.Playoff == True) & (df.Phase == 'ST') & (df.Year.isin([2015, 2016, 2017, 2018]))].groupby(['GroupPos']).mean().reset_index() ,s = 100, ax = ax_1)

# sns.scatterplot(x = 'Salary', y = 'WinShares', marker = '+', data = df[(df.Player == 'Patrick Mahomes')].groupby(['GroupPos']).mean().reset_index(), s= 50, ax = ax_1)
# sns.scatterplot(x = 'Salary', y = 'WinShares', marker = '+', data = df[(df.Player == 'Tom Brady')].groupby(['GroupPos']).mean().reset_index(), s= 50, ax = ax_1)
# sns.scatterplot(x = 'Salary', y = 'WinShares', marker = '+', data = df[(df.Player == 'Aaron Rodgers')].groupby(['GroupPos']).mean().reset_index(), s= 50, ax = ax_1)


# sns.regplot(x = 'Salary', y = 'WinShares', scatter = False,data = df[(df.Playoff == False) & (df.Year.isin([2015, 2016, 2017, 2018]))].groupby(['GroupPos']).mean().reset_index(),  ax = ax_2)
sns.scatterplot(x = 'Salary', y='WinShares', marker = 'o', hue = 'GroupPos', data= df[(df.Playoff == False) & (df.Phase == 'Off') & (df.Year.isin([2015, 2016, 2017, 2018]))].groupby(['GroupPos']).mean().reset_index() ,s = 100, ax = ax_2)
sns.scatterplot(x = 'Salary', y='WinShares', marker = 'X',hue = 'GroupPos', data= df[(df.Playoff == False) & (df.Phase == 'Def') & (df.Year.isin([2015, 2016, 2017, 2018]))].groupby(['GroupPos']).mean().reset_index() ,s = 100, ax = ax_2)
sns.scatterplot(x = 'Salary', y='WinShares', marker = 's',hue = 'GroupPos', data= df[(df.Playoff == False) & (df.Phase == 'ST') & (df.Year.isin([2015, 2016, 2017, 2018]))].groupby(['GroupPos']).mean().reset_index() ,s = 100, ax = ax_2)


fig.suptitle('WinShares by Salary for All Positions - Offense = \u25cf, Defense = X, Special Teams = \u25a0')
# plt.title('Offense = O, Defense = X, Special Teams = square', x = -0.14, y = 1.025)

ax_1.set_title('Playoff Teams')
ax_2.set_title('Non-Playoff Teams')
ax_1.legend(loc = 'upper left', bbox_to_anchor = (-.35,.95))
ax_2.get_legend().remove()

plt.show()

data = df.groupby(['Year', 'GroupPos','Player','Team']).sum().reset_index()
newdata = pd.concat([data[data.GroupPos == i].sort_values(by = "WinShares", ascending = False).head() for i in data.GroupPos.unique()], axis = 0, sort = False)
pos = [i for i in newdata.GroupPos.unique()]
n = [[" ".join([str(j) for j in (i[0], i[1], "<b>WS:", round(i[2], 2))]) for i in newdata[newdata.GroupPos == i].sort_values(by = 'WinShares', ascending = False)[['Player', 'Year', 'WinShares']].values] for i in pos]

fig = go.Figure(data=[go.Table(
  header=dict(
    values=[""] + pos,
    line_color='darkslategray',
    fill_color='grey',
    align=['left','center'],
    font=dict(color='white', size=12)
  ),
  cells=dict(
    values=[["1", "2", "3", "4", "5"]] + n, 
    line_color='darkslategray',
    # 2-D list of colors for alternating rows
    fill_color = [["white","lightgrey","white","lightgrey","white"]*5],
    align = ['left', 'center'],
    font = dict(color = 'darkslategray', size = 8)
    ))
])

fig.show()