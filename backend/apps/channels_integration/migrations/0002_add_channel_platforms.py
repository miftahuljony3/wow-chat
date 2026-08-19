from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('channels_integration', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='channelintegration',
            name='platform',
            field=models.CharField(
                choices=[
                    ('whatsapp', 'WhatsApp Cloud API'),
                    ('messenger', 'Facebook Messenger'),
                    ('instagram', 'Instagram'),
                    ('telegram', 'Telegram'),
                    ('discord', 'Discord'),
                    ('web_chat', 'Web Chat Widget'),
                ],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='channelintegration',
            name='instagram_business_account_id',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='channelintegration',
            name='telegram_bot_token',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='channelintegration',
            name='telegram_bot_username',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='channelintegration',
            name='discord_bot_token',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='channelintegration',
            name='discord_guild_id',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='channelintegration',
            name='discord_channel_id',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='channelintegration',
            name='web_chat_widget_key',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name='channelintegration',
            name='web_chat_allowed_origins',
            field=models.TextField(blank=True, help_text='Newline-separated list of allowed origins'),
        ),
    ]
