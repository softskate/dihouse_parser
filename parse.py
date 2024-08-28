import imaplib
import email
import os
import openpyxl
from database import Product, App, Crawl
from keys import EMAIL_ACCOUNT, EMAIL_PASSWORD


IMAP_SERVER = 'imap.ya.ru'
SAVE_FOLDER = 'prices'


class Parser:
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    def save_attachment(self, part, folder):
        if not os.path.isdir(folder):
            os.makedirs(folder)
        filename = part.get_filename()
        if filename:
            filepath = os.path.join(folder, filename)
            with open(filepath, 'wb') as f:
                f.write(part.get_payload(decode=True))
            return filepath


    def process_email_message(self, msg):
        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue
            filepath = self.save_attachment(part, SAVE_FOLDER)
            return self.parse(filepath)


    def start(self):
        complated = False
        self.mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        self.mail.select('inbox')

        # Поиск всех непрочитанных сообщений
        status, data = self.mail.search(None, 'UNSEEN')
        mail_ids = data[0].split()

        for mail_id in mail_ids:
            status, msg_data = self.mail.fetch(mail_id, '(RFC822)')
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            subject = msg.get('subject', 'No Subject').strip()
            sender = msg.get('From')
            if subject == 'Price Di-house' or sender == 'babushkin@di-house.ru':
                outcome = self.process_email_message(msg)
                if outcome:
                    complated = True
                    self.mail.store(mail_id, '+FLAGS', '\\Seen')


        self.mail.logout()
        return complated


    def parse(self, file_path):
        workbook = openpyxl.load_workbook(file_path)
        sheet = workbook.active
        translator = {
            'Бренд': 'brandName',
            'Артикул': 'sku',
            'Номенклатура.Код': 'productId',
            'EAN': 'ean',
            'Номенклатура.Наименование для печати': 'name',
            'В Наличии': 'qty',
            'Ваша цена': 'price',
            'Цена РРЦ': 'priceRRC'
        }

        headers = [translator[cell.value] for cell in sheet[1]]
        tree = {}
        data = []
        appid = App.create(name='Di-House')
        crawlid = Crawl.create()
        for row in sheet.iter_rows(min_row=2):
            if row[0]._style[0] == 2:
                lvl = row[0]._style[5]
                if lvl > 1: lvl -= 1
                tree[lvl] = row[0].value
                while True:
                    lvl += 1
                    if tree.get(lvl) is None: break
                    tree.pop(lvl)
                continue

            row_data = {headers[i]: row[i].value for i in range(len(headers))}
            row_data['category'] = ' - '.join(tree.values())
            row_data['appid'] = appid
            row_data['crawlid'] = crawlid
            Product.create(**row_data)
            data.append(row_data)

        crawlid.finished = True
        crawlid.save()

        return data

