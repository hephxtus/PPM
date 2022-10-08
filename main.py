"""
Small script to clean up passwords exported from chrom as the tend to have multiple entries for the same url
"""
import os
from urllib.parse import urlsplit

import pandas as pd
import tldextract as tldextract


def load_passwords(abs_file_path):
    """
    load the passwords from the csv file into a dataframe
    :param abs_file_path:
    :return:
    """
    passwords_df = pd.read_csv(abs_file_path)
    passwords_df.rename(columns=passwords_df.iloc[0])
    column_names = passwords_df.columns
    return passwords_df, column_names


def find_duplicates(passwords_df):
    """
    find duplicates in the passwords_df

    :param passwords_df:
    :return: passwords_temp - df without duplicates (same url, username, and password)
    :return: possible_duplicates - possible duplicates (same url and username, but different password)
    :return: possible_outdated - possible outdated logins (same url, different username and password)

    """
    passwords_copy = passwords_df.copy()
    passwords_copy['group'] = passwords_df['url'].apply(lambda x: tldextract.extract(str(x)).domain)

    passwords_copy['f_username'] = passwords_df['username'].apply(lambda x: str(x).lower())
    # delete rows with the same username, url and password
    passwords_copy.drop_duplicates(subset=['f_username', 'group', 'password'], keep='first', inplace=True)
    # find the duplicates (ie rows with the same username and url)
    possible_duplicates = passwords_copy[passwords_copy.duplicated(subset=['group', 'f_username'], keep=False)]
    # add rows with the same url and password but different username
    possible_duplicates = possible_duplicates.append(passwords_copy[passwords_copy.duplicated(subset=['group', 'password'], keep=False)])
    # sort the duplicates by url -> username -> password
    possible_duplicates = possible_duplicates.sort_values(by=['group', 'f_username', 'password'])
    # find potentially outdated entries (ie same url) and not same username
    possible_outdated = passwords_copy[passwords_copy.duplicated(subset=['group'], keep=False)]
    possible_outdated = possible_outdated[~possible_outdated['f_username'].isin(possible_duplicates['f_username'])]
    # sort the outdated by url -> username -> password
    possible_outdated = possible_outdated.sort_values(by=['group', 'f_username', 'password'])

    # remove hostname and f_username columns
    possible_duplicates = possible_duplicates.drop(columns=['f_username'])
    possible_outdated = possible_outdated.drop(columns=['f_username'])
    passwords_copy = passwords_copy.drop(columns=['f_username'])

    return passwords_copy, possible_duplicates, possible_outdated


def delete_null_rows(passwords_df):
    """
    delete rows with null values
    :param passwords_df:
    :return: passwords df without null values
    """
    return passwords_df.dropna()


def band_aid_fix(old_passwords, new_passwords):
    """band-aid fix for the duplicates to replace the url from new_passwords with the url from password
        and the username from new_passwords with the username from passwords"""
    for index, row in old_passwords.iterrows():
        new_passwords.loc[new_passwords['url'] == urlsplit(str(row['url'])).hostname, 'url'] = row['url']
        new_passwords.loc[new_passwords['username'] == str(row['username']).lower(), 'username'] = row['username']
    return new_passwords


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # get path to the passwords file
    path_to_file = input('Enter path to passwords file: ')
    try:
        # get absolute path to the file
        path_to_file = os.path.abspath(path_to_file)

        # load the passwords file into a dataframe and get the column names
        passwords, headers = load_passwords(path_to_file)

        # delete rows with null values
        passwords = delete_null_rows(passwords)

        # remove duplicates, and find possible duplicates and outdated entries
        passwords, duplicates, outdated = find_duplicates(passwords)

        if duplicates.empty:
            print('No duplicates found')
        else:             # print index of possible duplicates in the original file
            print("=============POSSIBLE DUPLICATED ENTRIES:=============")
            duplicates_dict = duplicates.groupby(['group', 'username']).groups
            for key, value in duplicates_dict.items():
                print(f"domain: {key}, index: {value}")

        if outdated.empty:
            print('No outdated entries found')
        else:             # print index of possible outdated entries in the original file
            print("=============POSSIBLE OUTDATED ENTRIES:=============")
            outdated_dict = outdated.groupby(['group']).groups
            for key, value in outdated_dict.items():
                print(f"domain: {key}, index: {value}")

        # export the cleaned up passwords to a new file
        if 'group' not in headers:
            headers.append('group')
        passwords.to_csv('data/exported_passwords.csv', index=False, header=headers)
    except FileNotFoundError:
        print(f'File {path_to_file} not found')
        exit(1)
    except Exception as e:
        print(e)
        exit(1)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
