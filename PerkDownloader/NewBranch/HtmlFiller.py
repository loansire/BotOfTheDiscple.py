from bs4 import BeautifulSoup
import os

def CopyTemplate():
    with open('../CurrentLostSector/Template.html', 'r', encoding='utf-8') as file:
        html_file = BeautifulSoup(file, 'lxml')

    with open('../CurrentLostSector/Output.html', 'w', encoding='utf-8') as file:
        file.write(str(html_file))


def MainInfos(activity_name, activity_description, background_image, activity_place, activity_destination, rewards):
    with open('../CurrentLostSector/Output.html', 'r', encoding='utf-8') as file:
        html_file = BeautifulSoup(file, 'lxml')


    ######################################## Main infos #########################################################
    #Get html variables
    html_activity_name = html_file.find(id="activity_type")
    html_activity_place_and_destination = html_file.find(id="activity_name")
    html_activity_background_image = html_file.find(id="activity_description")


    #Fill the html
    if html_activity_name:
        html_activity_name.string = activity_name

    if html_activity_place_and_destination:
        html_activity_place_and_destination.string = activity_place + " - " + activity_destination

    if html_activity_background_image:
        html_activity_background_image['src'] = background_image


    ########################################## Rewards #######################################################
    #Reward names

    span_elements = html_file.find_all('span')

    #Reward 1
    html_reward_1 = html_file.find(id="reward_name_1")
    reward_splitted = TreatRewardText(rewards[0][1])
    parsed_html = BeautifulSoup(reward_splitted[0] + '<br/><span class="small-text">' + reward_splitted[1] + "</span>", 'html.parser')
    html_reward_1.clear()
    html_reward_1.append(parsed_html)

    html_reward_icon_1 = html_file.find(id="reward_icon_1")
    html_reward_icon_1['src'] = rewards[0][2]

    #Reward 2
    html_reward_1 = html_file.find(id="reward_name_2")
    reward_splitted = TreatRewardText(rewards[1][1])
    parsed_html = BeautifulSoup(reward_splitted[0] + '<br/><span class="small-text">' + reward_splitted[1] + "</span>", 'html.parser')
    html_reward_1.clear()
    html_reward_1.append(parsed_html)

    html_reward_icon_1 = html_file.find(id="reward_icon_2")
    html_reward_icon_1['src'] = rewards[1][2]

    #Reward 3
    html_reward_1 = html_file.find(id="reward_name_3")
    reward_splitted = TreatRewardText(rewards[2][1])
    parsed_html = BeautifulSoup(reward_splitted[0] + '<br/><span class="small-text">' + reward_splitted[1] + "</span>", 'html.parser')
    html_reward_1.clear()
    html_reward_1.append(parsed_html)

    html_reward_icon_1 = html_file.find(id="reward_icon_3")
    html_reward_icon_1['src'] = rewards[2][2]


    with open('../CurrentLostSector/Output.html', 'w', encoding='utf-8') as file:
        file.write(str(html_file))
    



def TreatRewardText(reward_text):
    reward_text = reward_text.replace("En solo - ", "")

    name_rarity_split = reward_text.split(" (")
    name = name_rarity_split[0].replace(" ", "<br/>")
    rarity = "(" + name_rarity_split[1]
    
    return [name, rarity]
