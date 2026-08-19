import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('automation', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='autopostconfig',
            name='reply_persona',
            field=models.TextField(blank=True, help_text="Tone / personality for AI replies (e.g. 'friendly and upbeat, uses the customer's name, adds one emoji')."),
        ),
        migrations.AddField(
            model_name='autopostconfig',
            name='business_context',
            field=models.TextField(blank=True, help_text='Facts the AI can use when replying — hours, prices, location, products, FAQs.'),
        ),
        migrations.AddField(
            model_name='autopostconfig',
            name='reply_language',
            field=models.CharField(choices=[('auto', "Match commenter's language"), ('en', 'English'), ('bn', 'Bengali'), ('hi', 'Hindi'), ('ar', 'Arabic'), ('es', 'Spanish')], default='auto', max_length=8),
        ),
        migrations.AddField(
            model_name='autopostconfig',
            name='like_valid_comments',
            field=models.BooleanField(default=False, help_text="Also 'like' comments classified as valid."),
        ),
        migrations.AddField(
            model_name='autopostconfig',
            name='reply_only_to_questions',
            field=models.BooleanField(default=False, help_text='Only auto-reply when the comment is a question or clearly expects a response.'),
        ),
        migrations.AddField(
            model_name='autopostconfig',
            name='total_replies_sent',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.CreateModel(
            name='CommentAutoReplyRule',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(blank=True, max_length=100)),
                ('keywords', models.CharField(help_text="Comma-separated trigger keywords (e.g. 'price, cost, how much').", max_length=500)),
                ('match_type', models.CharField(choices=[('any', 'Match ANY keyword'), ('all', 'Match ALL keywords'), ('exact', 'Exact phrase')], default='any', max_length=8)),
                ('reply_text', models.TextField(help_text='The canned reply to post.')),
                ('is_active', models.BooleanField(default=True)),
                ('priority', models.PositiveIntegerField(default=0, help_text='Higher priority rules are checked first.')),
                ('times_triggered', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('config', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reply_rules', to='automation.autopostconfig')),
            ],
            options={
                'verbose_name': 'Comment Auto-Reply Rule',
                'verbose_name_plural': 'Comment Auto-Reply Rules',
                'ordering': ['-priority', 'created_at'],
            },
        ),
    ]
