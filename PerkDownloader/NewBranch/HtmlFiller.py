from bs4 import BeautifulSoup
import os

def CopyTemplate():
    with open('../CurrentLostSector/Template.html', 'r', encoding='utf-8') as file:
        html_file = BeautifulSoup(file, 'lxml')

    with open('../CurrentLostSector/Output.html', 'w', encoding='utf-8') as file:
        file.write(str(html_file))


def MainInfos(activity_name, activity_description, background_image):
    with open('../CurrentLostSector/Output.html', 'r', encoding='utf-8') as file:
        html_file = BeautifulSoup(file, 'lxml')

    #Get html variables
    html_activity_name = html_file.find("h1", class_="Activity-Name")
    html_activity_description = html_file.find("p", class_="Activity-Description")
    html_activity_background_image = html_file.find("img", class_="background-image")


    #Fill the html
    if html_activity_name:
        html_activity_name.string = activity_name

    if html_activity_description:
        html_activity_description.string = activity_description

    if html_activity_background_image:
        html_activity_background_image['src'] = background_image

    with open('../CurrentLostSector/Output.html', 'w', encoding='utf-8') as file:
        file.write(str(html_file))
    

