# WinShares

Repository for creating WinShares in the NFL.

WinSharesTest.py - Class for scraping data from Pro Football Reference and calculating WinShares for years 2014-2018. 

MaddenTest.py - Class to run correlation tests with WinShares and Madden Overalls for years 2014-2018

data - Folder with csv files of WinShares data and Madden rosters

## Usage

All WinShares from the past 5 years are stored as csv files in the data folder. To calculate WinShares, run WinSharesTest.py and use the win_shares method in the WinShares class. The method returns a dataframe with each player's win shares calculated for each week in the given year (it can also handle multiple years). The dataframe has columns for each player's snap count (OffNum, DefNum, STNum, OffPct, DefPct, STPct) and the WPA for the team (TeamAdjOffWPA, TeamAdjDefWPA, TeamAdjSTWPA, TeamGameWPA) and player (OffWPA, DefWPA, STWPA, TotWPA).

The MaddenTest.py file was used to run the correlation tests and the comparison method in the MaddenTest class returns a dataframe with all the players' cumulative win shares and Week 1 Madden Overall for each year inputted. 
