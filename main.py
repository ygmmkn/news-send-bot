import discord
from discord import app_commands 
from discord.ext import tasks
import configparser
import requests
import datetime

intents = discord.Intents.all()
intents.message_content = True  # 
intents.members = True
config_ini = configparser.ConfigParser()
config_ini.read('config.ini', encoding='utf-8')

def request_api(url):
    return requests.get(url).json()

def get_day_of_week_jp(time):
    date  = time[0:10]
    dt = datetime.datetime.strptime(date, '%Y-%m-%d')
    w_list = ['月曜日', '火曜日', '水曜日', '木曜日', '金曜日', '土曜日', '日曜日']
    return('(' + w_list[dt.weekday()][0:1] + ')')

def add_embed_overview_forecast(publishing_office, target_area, headline_text, text, area_code):
    text_fixed = ''
    if headline_text == '':
        text_fixed =  text
    else:
        text_fixed = headline_text + '\n' + text

    embed = discord.Embed(title = str(target_area+'の天気の概要'), 
                          description =  str(text_fixed),
                          color = int('0x5A9DE0', 16),
                          url = f'https://www.jma.go.jp/bosai/#pro&disp=forecast_table,weather_map!now,himawari!ir,radar,amedas!temp,amedas_table&col=dhdhdhdhrd&row=b4b4b4&area_type=offices&area_code={area_code}'
                          )
    embed.set_author(name = publishing_office, )
    return embed

def add_embed_forecast(publishing_office, area, weather_code, weather, pop, temp, area_code, date_time):
    day_of_week = get_day_of_week_jp(date_time)
    date_month_day = ''
    if date_time[5] == '0':
        date_month_day = date_time[6:10].replace('-', '/')
    else:
        date_month_day = date_time[5:10].replace('-', '/')
    embed = discord.Embed(title = str(f'{area}の{date_month_day}{day_of_week}の天気予報'), 
                          description =  str(weather),
                          color = int('0x5A9DE0', 16),
                          url = f'https://www.jma.go.jp/bosai/#pro&disp=forecast_table,weather_map!now,himawari!ir,radar,amedas!temp,amedas_table&col=dhdhdhdhrd&row=b4b4b4&area_type=offices&area_code={area_code}'
                          )
    embed.set_thumbnail(url=f'https://weathernews.jp/s/topics/img/wxicon/{weather_code}.png')
    embed.add_field(name='降水確率',value=str(pop+'%'))
    embed.add_field(name='気温',value=str(temp[0]+'℃/'+temp[1]+'℃'))
    embed.set_author(name = publishing_office, )
    return embed

class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self) 
    async def setup_hook(self):
        for id in MY_GUILDS:
            self.tree.copy_global_to(guild=id)
            await self.tree.sync(guild=id)
    
client = MyClient(intents=intents)

MY_GUILDS = [discord.Object(id=config_ini.getint('GUILD', 'guild_id_1')),
             discord.Object(id=config_ini.getint('GUILD', 'guild_id_2'))]

area_code = config_ini.get('AREA', 'area')

overview_forecast_url = f'https://www.jma.go.jp/bosai/forecast/data/overview_forecast/{area_code}.json'
forecast_url = f'https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json'

@tasks.loop(seconds=60) #60秒毎
async def send_message():
    dt_now = datetime.datetime.now()
    current_time = dt_now.hour
    if current_time == 6 or current_time == 21:

        overview_forecast_data  = request_api(overview_forecast_url)
        ov_fc_report_time_current = overview_forecast_data['reportDatetime'] 
        ov_fc_report_time_recorded = ''
        # txtファイルに記録されているデータ更新の時刻を取得する
        with open('overview_forecast_time.txt', mode='r') as f:
            # ファイルの読み込んで変数に代入
            ov_fc_report_time_recorded = f.read()
        f.close

        # 情報が更新された場合に条件分岐
        if ov_fc_report_time_recorded != ov_fc_report_time_current:
            publishing_office = overview_forecast_data['publishingOffice'] 
            target_area = overview_forecast_data['targetArea'] 
            headline_text = overview_forecast_data['headlineText']
            text = overview_forecast_data['text'].replace('\n\n', '\n') 
            print('overview_forecast '+ov_fc_report_time_current)
            embed = add_embed_overview_forecast(publishing_office, target_area, headline_text, text, area_code)
            guild = [discord.utils.find(lambda g: g.id == config_ini.getint('GUILD', 'guild_id_1'), client.guilds),
                    discord.utils.find(lambda g: g.id == config_ini.getint('GUILD', 'guild_id_2'), client.guilds)]
            channel = [guild[0].get_channel(config_ini.getint('CHANNEL', 'channel_id_ov_fc')),
                    guild[1].get_channel(config_ini.getint('CHANNEL', 'channel_id_ov_fc_2'))]
            await channel[0].send(embed=embed)
            await channel[1].send(embed=embed)
            # 書き込む
            with open('overview_forecast_time.txt', 'w', encoding='UTF-8', newline='\n') as f:
                data = ov_fc_report_time_current
                f.writelines(data)
            f.close()
            print('ov_fc sent '+ov_fc_report_time_current)
        
        if current_time == 21:
            forecast_data  = request_api(forecast_url)
            fc_report_time_current = forecast_data[0]['reportDatetime']
            fc_report_time_recorded = ''
            # txtファイルに記録されているデータ更新の時刻を取得する
            with open('forecast_time.txt', mode='r') as f:
                # ファイルの読み込んで変数に代入
                fc_report_time_recorded = f.read()
            f.close
            if fc_report_time_recorded != fc_report_time_current:
                publishing_office = forecast_data[0]['publishingOffice']

                tomorrow_forecast_data = forecast_data[0]['timeSeries'] 
                weather_code = tomorrow_forecast_data[0]['areas'][0]['weatherCodes'][1]
                area = tomorrow_forecast_data[0]['areas'][0]['area']['name']
                weather = tomorrow_forecast_data[0]['areas'][0]['weathers'][1] 
                pop = tomorrow_forecast_data[1]['areas'][0]['pops'][1]
                temp = tomorrow_forecast_data[2]['areas'][0]['temps'] 
                time = tomorrow_forecast_data[0]['timeDefines'][1]
                print('forecast '+fc_report_time_current)
                embed = add_embed_forecast(publishing_office, area, weather_code, weather, pop, temp, area_code,time)
                guild = [discord.utils.find(lambda g: g.id == config_ini.getint('GUILD', 'guild_id_1'), client.guilds),
                        discord.utils.find(lambda g: g.id == config_ini.getint('GUILD', 'guild_id_2'), client.guilds)]
                channel = [guild[0].get_channel(config_ini.getint('CHANNEL', 'channel_id_fc')),
                        guild[1].get_channel(config_ini.getint('CHANNEL', 'channel_id_fc_2'))]
                await channel[0].send(embed=embed)
                await channel[1].send(embed=embed)
            # 書き込む
                with open('forecast_time.txt', 'w', encoding='UTF-8', newline='\n') as f:
                    data = fc_report_time_current
                    f.writelines(data)
                f.close()
                print('fc sent '+fc_report_time_current)
            else:
                return
    
@client.event
async def on_ready(): #botログイン完了時に実行
    print('on_ready') 
    send_message.start()

client.run(config_ini.get('TOKEN', 'token')) 
