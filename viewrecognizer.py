# -*- coding: utf-8 -*-
"""
 画像認識処理
"""
import PIL.Image
import PIL.ImageGrab, PIL.ImageOps

import numpy
#import cv2
import pyocr

import time

import json
import ast

import difflib
import itertools

import concurrent.futures

import logging

class UmaAdvChoiceRecognizer:
    """画面キャプチャから選択肢の情報を取得する"""
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(logging.NullHandler())
        
        #self.event_info = self.load_eventinfo_json("info.json")
        self.event_info = self.convert_eventchecker_data()
        self.OCR = self.init_OCR()

        self.binarize_threshold = 200 #MEMO: 決め打ち
        self.base_geometry_info = {
            'size_window_client': (429, 762),
            'rect_event_title': (63, 140, 279, 172),
            'ret_selection_region': (34, 189, 382, 689),
            }

    #---
    def load_eventinfo_json(self, filename):
        """イベント情報をjsonファイルからロード"""
        raise NotImplementedError()
    def convert_eventchecker_data(self, filename = "female_event_datas.js"):
        """
         INFO: イベントチェッカーのデータを拝借
        """
        infile = open(filename, 'r', encoding='utf-8')
        ret = []
        for line in infile:
            if line.find("];") >= 0: break
            if line[0] != "{": continue
            
            line = line.rstrip(",\n")
            rd = ast.literal_eval(line)
            # 整形
            if rd['c'] == "s": rd['n'] = rd['n'] + "(" + rd['l'] + ")"
            cs = []
            for c in rd['choices']:
                if c['n'].startswith("選択肢なし"): continue
                cs.append((c['n'], c['t'].replace("[br]", "\n").replace("<hr>", "／")))
            d = (rd['e'], rd['n'], cs)
            
            self.logger.debug(d)
            ret.append(d)

        return ret

    #---
    def init_OCR(self):
        """initialize OCR tool"""
        tools = pyocr.get_available_tools()
        if not tools:
            raise FileNotFoundError("OCR tool not found(Please install 'Tesseract')")
        for t in tools:
            self.logger.info(t.get_name())

        return tools[0]

    def extract_event_view(self, imagecap):
        """
         キャプチャ画像から解析に必要な部分を抜き出す
        """
        # クライアント領域のサイズ比から座標を計算
        wndr = [imagecap.size[i] / self.base_geometry_info['size_window_client'][i] for i in range(2)]
        reg_ttl = [int(self.base_geometry_info['rect_event_title'][i] * wndr[i % 2]) for i in range(len(self.base_geometry_info['rect_event_title']))]
        reg_sel = [int(self.base_geometry_info['ret_selection_region'][i] * wndr[i % 2]) for i in range(len(self.base_geometry_info['ret_selection_region']))]

        # 境界線を探すために画像を2値化する
        imgray = imagecap.convert('L')
        im_ttl = PIL.ImageOps.invert(imgray.crop(reg_ttl).point(lambda p: 0 if p < self.binarize_threshold else p))
        im_sel = imgray.crop(reg_sel).point(lambda p: 0 if p < self.binarize_threshold else p)

        ret = {'grayscale': imgray, 'title': im_ttl, 'selections': []}

        #-- 選択肢の枠(白色長方形)を探して画像を抜き出す
        arr_sel = numpy.asarray(im_sel)
        lsum = arr_sel.sum(axis = 1) # 水平方向ピクセルの和
        th = 255 * arr_sel.shape[1] // 4 # これ以上白い部分が大きければ枠とみなす(MEMO: 補正で背景は真っ黒になっているので雑な値で問題ない)
        
        sty = None
        for cy in range(len(lsum)):
            if lsum[cy] > th:
                if sty is None: sty = cy
            elif sty is not None:
                im = imgray.crop((reg_sel[0], reg_sel[1] + sty, reg_sel[2], reg_sel[1] + cy)) # INFO: ここは背景が真っ白なので補正(2値化)しない状態で文字認識させている
                ret['selections'].append(im)
                sty = None
        
        return ret

    def OCR_event_view(self, wndimage):
        """
         イベントタイトルと選択肢を文字認識する
        """
        img = self.extract_event_view(wndimage)

        #stt = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []

            f = executor.submit(self.OCR.image_to_string, img['title'], lang = 'jpn', builder = pyocr.builders.TextBuilder(tesseract_layout = 6))
            futures.append(f)
            for ims in img['selections']:
                f = executor.submit(self.OCR.image_to_string, ims, lang = 'jpn', builder = pyocr.builders.TextBuilder(tesseract_layout = 6))
                futures.append(f)

            _ = concurrent.futures.as_completed(futures)

            rets = [f.result().replace(" ", "") for f in futures]

        #self.logger.debug("time: ", time.perf_counter() - stt)
        return (rets[0], rets[1:])

    def find_event_info(self, title, selection):
        """
         文字列類似度を基に該当のイベントを探す
         TODO: スコアの合算方法について検討する
           ひとまず タイトルと選択肢のスコアを全て加算で考える (「初詣」「武骨」のように漢字がうまく識別できない短文が難しい)
        """
        sm_ttl = difflib.SequenceMatcher(b = title)
        sm_sel = [difflib.SequenceMatcher(b = t) for t in selection]
        ns = len(selection)
        
        max_rat = 0.0
        max_mat = None
        for ev in self.event_info:
            it = ev[0]
            isl = ev[2]
            if len(isl) != ns: continue

            sm_ttl.set_seq1(it)
            #rt = sm_ttl.quick_ratio()
            rt = sm_ttl.ratio() #MEMO: OCRの方が圧倒的に高コストだった
            if rt + ns < max_rat: continue # 類似度は最大1.0なので打ち切り(MEMO: 合算方法が変わるとこの部分も変更必要)

            for j in range(ns):
                sm_sel[j].set_seq1(isl[j][0])
                rt = rt + sm_sel[j].ratio()
                if rt + ns - j - 1 < max_rat: continue
                
            if rt > max_rat:
                max_rat = rt
                max_mat = ev
        
        self.logger.debug("%s %s", title, selection)
        self.logger.debug("%f, %s", max_rat, max_mat)
        return max_mat


#---
def main():
    ocr = UmaAdvChoiceRecognizer()

    event_info = ocr.convert_eventchecker_data()
    for e in event_info:
    	print(e)
    
    r = ocr.find_event_info("~上々の面捕えッチ", ['では、新しい練習用具をいただけますか?', 'では、にんじんを分けていただけますか?'])
    print(r)
    

#----
if __name__ == "__main__":
    main()
