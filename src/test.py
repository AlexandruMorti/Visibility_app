# import pandas as pd

# df = pd.read_csv("dives_with_conditions.csv")
# print(df)
# print("Rows:", len(df))
# print(df.isna().sum())

# import pandas as pd
# df = pd.read_csv("dives_with_conditions.csv")
# print(df)
# print(df.isna().sum())



# import sqlite3, pandas as pd
# conn = sqlite3.connect("visibility.db")
# df = pd.read_sql_query("SELECT tide_height FROM conditions", conn)
# print(df.head(20))


# import sqlite3

# conn = sqlite3.connect("visibility.db")
# cursor = conn.cursor()

# def add_column_if_missing(table, column, coltype):
#     # Check if column exists
#     cursor.execute(f"PRAGMA table_info({table})")
#     columns = [row[1] for row in cursor.fetchall()]

#     if column not in columns:
#         print(f"Adding column {column} to {table}")
#         cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")
#     else:
#         print(f"Column {column} already exists in {table}")

# # Add your new dive fields
# add_column_if_missing("dives", "max_depth_m", "REAL")
# add_column_if_missing("dives", "breath_hold_s", "REAL")

# conn.commit()
# conn.close()

# print("Done.")


import os
import sqlite3
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "visibility.db")
import sqlite3, pandas as pd
conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query("SELECT * FROM conditions", conn)
print(df.head(20))


# from app import app as flask_app

# print("Looking for templates in:", flask_app.template_folder)


# import os
# import sqlite3
# import pandas as pd

# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DB_PATH = os.path.join(BASE_DIR, "visibility.db")   # <-- inside src

# print("Using DB from app:", DB_PATH)




# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DB_PATH = os.path.join(BASE_DIR, "visibility.db")  # <-- inside src

# print("Using DB from fetch:", DB_PATH)

# Using DB from app: C:\Users\symon\Desktop\Alex Spearfishing  Diving\Visibility_app\src\visibility.db
# Using DB from fetch: C:\Users\symon\Desktop\Alex Spearfishing  Diving\Visibility_app\src\visibility.db



# conn = sqlite3.connect(DB_PATH)
# cursor = conn.cursor()

#Add a docstring with usage examples for training the model. This will help users understand how to run the training script.

# import os
# os.makedirs("data", exist_ok=True)
# csv = """date,swell_height,swell_period,wind_speed,wind_dir,tide_height,turbidity,chlorophyll,visibility,region
# 2025-06-01,0.5,6,5,180,1.2,3.0,1.1,8.5,UK
# 2025-06-02,0.7,7,6,190,1.0,2.8,1.0,7.2,UK
# 2025-06-03,0.4,5,4,170,0.8,3.5,1.3,9.0,UK
# 2025-06-04,1.0,8,8,200,1.5,4.0,1.5,5.5,UK
# 2025-06-05,0.6,6,5,185,1.1,3.2,1.2,8.0,UK
# """
# with open("data/visibility.csv","w",encoding="utf-8") as f:
#     f.write(csv)
# print("Wrote data/visibility.csv")