import requests
from bs4 import BeautifulSoup
import pandas as pd
from collections import defaultdict
import tkinter as tk
from tkinter import ttk, Tk, Label, Button, Entry, StringVar, Scrollbar, Text
from PIL import Image, ImageTk
import os

def generate_fight_outcomes(fighters, matchups, current_matchup, current_outcome):
    if len(current_matchup) == len(matchups):
        yield current_outcome
    else:
        fighter1, fighter2 = matchups[len(current_matchup)]
        for winner in [fighter1, fighter2]:
            next_outcome = current_outcome + [(fighter1, fighter2, winner)]
            remaining_fighters = [fighter for fighter in fighters if fighter != winner]
            yield from generate_fight_outcomes(remaining_fighters, matchups, current_matchup + [1], next_outcome)

def scrape_career_statistics(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        fighter_name_elem = soup.find('span', {'class': 'b-content__title-highlight'})
        career_stats_elem = soup.find('div', {'class': 'b-list__info-box-left clearfix'})
        
        if fighter_name_elem and career_stats_elem:
            fighter_name = fighter_name_elem.text.strip()
            stats = {}
            stats_list = career_stats_elem.find_all('li')

            for stat in stats_list:
                stat_parts = stat.text.split(':')
                if len(stat_parts) == 2:
                    stat_name, stat_value = map(str.strip, stat_parts)
                    stats[stat_name] = stat_value

            return {'Name': fighter_name, **stats}
        else:
            print(f"Could not find fighter name or career statistics on {url}")
            return None
    else:
        print(f"Failed to fetch data from {url}")
        return None

def save_to_csv(stats_with_name, filename='ufc_fight_night_test.csv'):
    try:
        df = pd.read_csv(filename)
    except FileNotFoundError:
        df = pd.DataFrame()

    df = df.append(stats_with_name, ignore_index=True)
    df.to_csv(filename, index=False)

def get_fighter_urls(event_url):
    response = requests.get(event_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        table = soup.find('table', {'class': 'b-fight-details__table b-fight-details__table_style_margin-top b-fight-details__table_type_event-details js-fight-table'})

        fighter_urls = []

        if table:
            rows = table.find_all('tr')[1:11]
            for row in rows:
                fighters = row.find_all('td')[1:3]
                for fighter in fighters:
                    f = fighter.find_all('p', class_='b-fight-details__table-text')
                    for p in f:
                        fighter_url = p.find('a', class_='b-link_style_black', href=True)
                        if fighter_url:
                            fighter_urls.append(fighter_url['href'])

        return fighter_urls
    else:
        print(f"Failed to fetch data from {event_url}")
        return None

def on_submit():
    fighter_urls = get_fighter_urls(url_var.get())
    career_stats_list = [scrape_career_statistics(url) for url in fighter_urls if scrape_career_statistics(url) is not None]

    for career_stats in career_stats_list:
        save_to_csv(career_stats)

    try:
        df = pd.read_csv('ufc_fight_night_test.csv')
    except FileNotFoundError:
        result_text.insert(tk.END, f"CSV file 'ufc_fight_night_test.csv' not found.\n")
        result_text.config(state=tk.DISABLED)
        return

    pairs = [(row['Name'], df.iloc[i + 1]['Name']) for i, row in df.iloc[::2].iterrows() if i + 1 < len(df)]

    fighter_stats = defaultdict(dict)
    for _, row in df.iterrows():
        fighter_stats[row['Name']] = {'SLpM': row['SLpM'], 'Str. Acc.': row['Str. Acc.']}

    winner_list = []
    outcomes = list(generate_fight_outcomes(set(df['Name']), pairs, [], []))

    total_outcomes = len(outcomes)
    result_text.insert(tk.END, f"Total number of outcomes: {total_outcomes}\n")

    count = 1
    for outcome_index, outcome in enumerate(outcomes, start=1):
        for matchup in outcome:
            fighter1, fighter2, winner = matchup
            stats1, stats2 = fighter_stats[fighter1], fighter_stats[fighter2]
            slpm1, slpm2 = stats1["SLpM"], stats2["SLpM"]
            sa1 = float(stats1["Str. Acc."].strip('%')) / 100
            sa2 = float(stats2["Str. Acc."].strip('%')) / 100

            aslpm1 = slpm1 * sa1
            aslpm2 = slpm2 * sa2

            if aslpm1 > aslpm2:
                winner = fighter1
            else:
                winner = fighter2

            if winner not in winner_list:
                winner_list.append(winner)

    for winner in winner_list:
        result_text.insert(tk.END, f"Fight {count} Winner: {winner}\n")
        count += 1

    result_text.config(state=tk.DISABLED)
    os.remove('ufc_fight_night_test.csv')

# Create a simple GUI with styling
root = Tk()
root.title("UFC Fight Calculator")
root.configure(bg="#C5000C")  # Set background color

# Logo
logo_path = "path_to_your_logo.png"  # Replace with the path to your logo
if os.path.exists(logo_path):
    logo_image = Image.open(logo_path)
    logo_image = logo_image.resize((400, 250), Image.ANTIALIAS)
    logo_image = ImageTk.PhotoImage(logo_image)
    logo_label = Label(root, image=logo_image, bg="#C5000C")
    logo_label.image = logo_image  # To prevent garbage collection
    logo_label.pack()

label = Label(root, text="Enter UFC Event URL:", bg="#C5000C", fg="white", font=("Helvetica", 16))
label.pack()

url_var = StringVar()
url_entry = Entry(root, textvariable=url_var, width=50, font=("Helvetica", 12))
url_entry.pack()

submit_button = Button(root, text="Submit", command=on_submit, bg="white", fg="black", font=("Helvetica", 14))
submit_button.pack()

# Output box with scrollbar
output_frame = ttk.Frame(root, padding=(10, 10))
output_frame.pack(fill=tk.BOTH, expand=True)

result_text = Text(output_frame, wrap=tk.WORD, height=10, width=80, bg="white", fg="black", font=("Helvetica", 12))
result_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

scrollbar = ttk.Scrollbar(output_frame, command=result_text.yview)
scrollbar.grid(row=0, column=1, sticky="nsew")
result_text['yscrollcommand'] = scrollbar.set

root.mainloop()
