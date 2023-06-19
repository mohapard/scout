import streamlit as st
import pandas as pd
import datetime
import boto3
from dateutil.relativedelta import relativedelta
import altair as alt
import os

AWS_ACCESS_KEY_ID = st.secrets['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = st.secrets['AWS_SECRET_ACCESS_KEY']
st.write(AWS_ACCESS_KEY_ID)
# Define S3 bucket details
BUCKET_NAME = "tacticmedia"
CSV_FILE_NAME = "Scouting/players.csv"

positions = ['ST', 'RW','LW','CAM','CM','CDM', 'LB', 'RB','CB','GK']
skills = ['Speed', 'Agility', 'Stamina', 'Ball Control', 'Dribbling', 'Shot', 'Tackling', 'Goalkeeping Skills', 'Aerial Duels', 'Vision', 'Passing']

# Authenticate with AWS S3

s3 = boto3.resource("s3",
                    aws_access_key_id=AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

def load_player_data():
    try:
        obj = s3.Object(BUCKET_NAME, CSV_FILE_NAME)
        player_data = pd.read_csv(obj.get()["Body"], dtype=str)
        if 'date_of_birth' in player_data.columns:
            #player_data['date_of_birth'] = pd.to_datetime(player_data['date_of_birth'])
            player_data['date_of_birth'] =pd.to_datetime(player_data['date_of_birth'], format="%d/%m/%Y %H:%M", errors='coerce')
        if 'record_date' in player_data.columns:
            player_data['record_date'] = pd.to_datetime(player_data['record_date'])
        if 'last_modified' in player_data.columns:
            player_data['last_modified'] = pd.to_datetime(player_data['last_modified'])
        st.write(player_data)
        return player_data
    except Exception as e:
        st.write(e)
        st.write(player_data)
        return pd.DataFrame()

def save_player_data(player_data):
    if 'date_of_birth' in player_data.columns:
        player_data['date_of_birth'] = player_data['date_of_birth'].astype(str)
    if 'record_date' in player_data.columns:
        player_data['record_date'] = player_data['record_date'].astype(str)
    if 'last_modified' in player_data.columns:
        player_data['last_modified'] = player_data['last_modified'].astype(str)
    
    s3.Object(BUCKET_NAME, CSV_FILE_NAME).put(Body=player_data.to_csv(index=False))


def calculate_age(birth_date):
    birth_date = pd.to_datetime(birth_date, errors='coerce')
    if pd.isnull(birth_date):
        return None
    today = pd.to_datetime('today')
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age


player_data = load_player_data()
if len(player_data) > 0 and 'date_of_birth' in player_data.columns:
    player_data['date_of_birth'] = pd.to_datetime(player_data['date_of_birth'])
    player_data['age'] = player_data['date_of_birth'].apply(calculate_age)

pages = ["Player Statistics", "Data Summarization", "Add Player"]
page = st.sidebar.selectbox("Page", pages)

# Add all the required filters
with st.sidebar.container():
    st.header("Filters")
    selected_positions = st.multiselect("Position", options=positions) if 'primary_position' in player_data.columns else []
    selected_genders = st.multiselect("Gender", options=['Male', 'Female']) if 'gender' in player_data.columns else []
    selected_cities = st.multiselect("City/Area", options=player_data['city_area'].unique().tolist()) if 'city_area' in player_data.columns else []
    
    #selected_age = st.slider("Age", min_value=0, max_value=100, value=(player_data['age'].min(), player_data['age'].max())) if 'age' in player_data.columns else []
    #selected_age = st.slider("Age", min_value=0, max_value=100, step=1, value=(int(player_data['age'].min()), int(player_data['age'].max()))) if 'age' in player_data.columns else []
    min_age = int(player_data['age'].min()) if pd.notnull(player_data['age'].min()) else 0
    max_age = int(player_data['age'].max()) if pd.notnull(player_data['age'].max()) else 100
    selected_age = st.slider("Age", min_value=0, max_value=100, step=1, value=(min_age, max_age)) if 'age' in player_data.columns else []

# Apply filters
if len(player_data) > 0:
    filters = (player_data['primary_position'].isin(selected_positions) if selected_positions else True) & \
              (player_data['gender'].isin(selected_genders) if selected_genders else True) & \
              (player_data['city_area'].isin(selected_cities) if selected_cities else True) & \
              (player_data['age'].between(*selected_age) if selected_age else True)
    filtered_data = player_data[filters]
else:
    filtered_data = None

if page == "Player Statistics":
    st.title('Football Player Scouting - Player Statistics')

    st.subheader('Player List')
    if filtered_data is not None and not filtered_data.empty:
        player_to_view = st.selectbox('Select player to view', filtered_data['name'])
        indices = filtered_data[filtered_data['name'] == player_to_view].index
        st.table(filtered_data.loc[indices].T)
    else:
        st.write("No player data available.")

elif page == "Data Summarization":
    st.title('Football Player Scouting - Data Summarization')

    st.subheader('Data Summary')
    if filtered_data is not None and not filtered_data.empty:
        
        st.subheader('Positions Summary')
        if 'primary_position' in filtered_data.columns:
            positions_df = filtered_data['primary_position'].value_counts().rename_axis('Position').reset_index(name='Count')
            st.table(positions_df.set_index('Position'))

        st.subheader('Age Summary')
        if 'age' in filtered_data.columns:
            age_df = filtered_data['age'].value_counts().rename_axis('Age').reset_index(name='Count')
            st.table(age_df.set_index('Age'))

        st.subheader('Gender Summary')
        if 'gender' in filtered_data.columns:
            gender_df = filtered_data['gender'].value_counts().rename_axis('Gender').reset_index(name='Count')
            st.table(gender_df.set_index('Gender'))

        st.subheader('Skills by Position')
        for skill in skills:
            if skill in filtered_data.columns and 'primary_position' in filtered_data.columns:
                chart = alt.Chart(filtered_data).mark_bar().encode(
                    x='primary_position:N',
                    y=f'mean({skill}):Q',
                    color='primary_position:N',
                    tooltip=['primary_position', f'mean({skill})']
                ).properties(
                    title=f'{skill} by Position'
                )
                st.altair_chart(chart, use_container_width=True)

        st.subheader('Top Performers for Each Skill')
        for skill in skills:
            if skill in filtered_data.columns:
                top_performer = filtered_data[['name', skill]].sort_values(by=[skill], ascending=False).head(1)
                st.write(f'Top performer for {skill}: {top_performer["name"].values[0]} with score {top_performer[skill].values[0]}')

    else:
        st.write("No player data available.")


# Page: Add Player
elif page == "Add Player":
    st.title('Football Player Scouting - Add Player')

    # Define empty dictionary to hold form inputs
    player = {}

    # Personal Information
    st.subheader('Personal Information')
    player["name"] = st.text_input("Full Name")
    player["gender"] = st.selectbox("Gender", ['Male', 'Female'])
    player["date_of_birth"] = st.date_input("Date of Birth",min_value= datetime.date(1990, 1, 1))
    player["nationality"] = st.text_input("Nationality", value="Egypt")
    player["city_area"] = st.text_input("City/Area","Cairo")
    player["current_club"] = st.text_input("Current Club")
    player["contact_number"] = st.text_input("Contact Number")
    player["estimated_value"] = st.number_input("Estimated Value (in $EGP)", min_value=0)

    st.subheader('Physical Attributes')
    player["height"] = st.text_input("Height (cm)")
    player["weight"] = st.text_input("Weight (kg)")
    player["preferred_foot"] = st.selectbox("Preferred Foot", [ 'Right','Left', 'Both'])


    # Positional Data
    st.subheader('Positional Data')
    player["primary_position"] = st.selectbox("Primary Position", positions)
    player["secondary_positions"] = st.multiselect("Secondary Positions", positions)
    
    # Skill Data
    st.subheader('Skills Data')
    for skill in skills:
        player[skill] = st.slider(skill, min_value=0, max_value=10,value=0)

    st.subheader('Evaluation')
    player["general_comments"] = st.text_input("General Comments")
    player["strengths"] = st.text_input("Strengths")
    player["weaknesses"] = st.text_input("Weaknesses")
    player["injury"] = st.text_input("Injury History")
    player["record_date"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") # Record Date


    
    if st.button('Add Player'):
        player_df = pd.DataFrame(player)
        #player_data = player_data.append(player_df, ignore_index=True)
        player_data = pd.concat([player_data, player_df], ignore_index=True)
        #player_data.to_csv("players.csv")
        st.write(player_data)
        save_player_data(player_data)
        st.success("Player successfully added!")
