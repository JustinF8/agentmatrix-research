"""GTJA191 (国泰君安 Alpha191) 因子库 —— 完整 191 因子实现

公式严格还原自 qlib-factor-zoo 的 ``qlib/contrib/data/loader_gtja191.py``
（即国泰君安 2014 年 Alpha191 研报的聚宽/qlib 对齐版本）。
每个因子以 qlib 表达式字符串形式保存（即公式源码），由 ``_expr_engine`` 求值。
"""
from __future__ import annotations

import re
import numpy as np
import pandas as pd

from research_core.factor_lab.operators import sort_panel
from research_core.factor_lab.libraries.gtja191._expr_engine import evaluate

# 原始 qlib 表达式（公式源码），key = alpha1..alpha191
GTJA_EXPRESSIONS: dict[str, str] = {
    "alpha1": 'Rank(-1*Corr(Rank(Delta(Log($volume+1),1),6), Rank(($close-$open)/$open,6), 6), 1)',
    "alpha2": '-1*Delta((($close-$low)-($high-$close))/($high-$low+1e-12), 1)',
    "alpha3": 'Sum(If($close>Ref($close,1), $close-Less($low,Ref($close,1)), If($close<Ref($close,1), $close-Greater($high,Ref($close,1)), 0)), 6)',
    "alpha4": 'If(Mean($close,8)+Std($close,8)<Mean($close,2), -1, If(Mean($close,2)<Mean($close,8)-Std($close,8), 1, If($volume/Mean($volume,20)>1, 1, -1)))',
    "alpha5": '-1*Max(Corr(Rank($volume,5), Rank($high,5), 5), 3)',
    "alpha6": '-1*Rank(Sign(Delta($open*0.85+$high*0.15, 4)), 1)',
    "alpha7": '(Rank(Max($vwap-$close,3),1)+Rank(Min($vwap-$close,3),1))*Rank(Delta($volume,3),1)',
    "alpha8": '-1*Rank(Delta((($high+$low)/2)*0.2+$vwap*0.8, 4), 1)',
    "alpha9": 'SMA((($high+$low)/2-(Ref($high,1)+Ref($low,1))/2)*($high-$low)/($volume+1e-12), 7, 2)',
    "alpha10": 'Rank(Max(Power(If($close/Ref($close,1)-1<0, Std($close/Ref($close,1)-1,20), $close), 2), 5), 1)',
    "alpha11": 'Sum((($close-$low)-($high-$close))/($high-$low+1e-12)*$volume, 6)',
    "alpha12": 'Rank($open-Sum($vwap,10)/10,1)*(-1*Rank(Abs($close-$vwap),1))',
    "alpha13": 'Power($high*$low, 0.5)-$vwap',
    "alpha14": 'Delta($close, 5)',
    "alpha15": '$open/Ref($close,1)-1',
    "alpha16": '-1*Max(Rank(Corr(Rank($volume,1), Rank($vwap,1), 5), 1), 5)',
    "alpha17": 'Sign(Rank($vwap-Max($vwap,15),1))*Power(Abs(Rank($vwap-Max($vwap,15),1)), Abs(Delta($close,5)))',
    "alpha18": '$close/Ref($close, 5)',
    "alpha19": 'If($close<Ref($close,5), ($close-Ref($close,5))/Ref($close,5), If($close>Ref($close,5), ($close-Ref($close,5))/$close, 0))',
    "alpha20": '($close-Ref($close,6))/Ref($close,6)*100',
    "alpha21": 'Slope(Mean($close,6), 6)/$close',
    "alpha22": 'SMA(($close-Mean($close,6))/Mean($close,6)-Ref(($close-Mean($close,6))/Mean($close,6),3), 12, 1)',
    "alpha23": 'SMA(If($close>Ref($close,1), Std($close,20), 0), 20, 1)/(SMA(If($close>Ref($close,1), Std($close,20), 0), 20, 1)+SMA(If($close<=Ref($close,1), Std($close,20), 0), 20, 1)+1e-12)*100',
    "alpha24": 'SMA(Delta($close,5), 5, 1)',
    "alpha25": '(-1*Rank(Delta($close,7)*(1-Rank(WMA($volume/Mean($volume,20),9),1)),1))*(1+Rank(Sum($close/Ref($close,1)-1,60),1))',
    "alpha26": '(Mean($close,7)-$close)+Corr($vwap, Ref($close,5), 30)',
    "alpha27": 'WMA(($close-Ref($close,3))/Ref($close,3)*100+($close-Ref($close,6))/Ref($close,6)*100, 12)',
    "alpha28": '3*SMA(($close-Min($low,9))/(Max($high,9)-Min($low,9)+1e-12)*100,3,1)-2*SMA(SMA(($close-Min($low,9))/(Max($high,9)-Min($low,9)+1e-12)*100,3,1),3,1)',
    "alpha29": '($close-Ref($close,6))/Ref($close,6)*$volume',
    "alpha30": 'WMA(($close/Ref($close,1)-1)*100, 2)',
    "alpha31": '($close-Mean($close,12))/Mean($close,12)*100',
    "alpha32": '-1*Corr($high, Rank($volume,1), 5)',
    "alpha33": '-1*Min($low,5)+Ref(Min($low,5),5)',
    "alpha34": 'Mean($close,12)/$close',
    "alpha35": '($open-Ref($close,1))/Ref($close,1)*$volume',
    "alpha36": 'Rank(Corr($close,$volume,15),1)*Rank(Delta($close,5),1)',
    "alpha37": '-1*Rank(Delta($open,1),1)',
    "alpha38": 'If(Mean($high,20)<$high, -1*Delta($high,2), 0)',
    "alpha39": 'Delta($close,7)*(1-Rank(WMA($volume/Mean($volume,20),9),1))*(-1)',
    "alpha40": 'Sum(If($close>Ref($close,1), $volume, 0), 26)/(Sum(If($close<=Ref($close,1), $volume, 0), 26)+1e-12)',
    "alpha41": '-1*Rank(Max(Delta($vwap,3),5),1)',
    "alpha42": '-1*Rank(Std($high,10),1)*Corr($high,$volume,10)',
    "alpha43": 'Sum(If($close>Ref($close,1), $volume, If($close<Ref($close,1), -$volume, 0)), 6)',
    "alpha44": 'Rank(WMA(Corr($low,Mean($volume,10),8),6),4)',
    "alpha45": '-1*Rank(Delta(Mean($close,5),2),1)*Rank(Corr($close,$open,5),1)',
    "alpha46": '(Mean($close,3)+Mean($close,6)+Mean($close,12)+Mean($close,24))/(4*$close)',
    "alpha47": 'SMA((Max($high,6)-$close)/(Max($high,6)-Min($low,6)+1e-12)*100, 9, 1)',
    "alpha48": '-1*Rank(Sign($close-Ref($close,1))+Sign(Ref($close,1)-Ref($close,2))+Sign(Ref($close,2)-Ref($close,3)),1)*Sum($volume,5)/Sum($volume,20)',
    "alpha49": 'Sum(If($high+$low>=Ref($high,1)+Ref($low,1), 0, Greater(Abs($high-Ref($high,1)),Abs($low-Ref($low,1)))), 12)/(Sum(If($high+$low>=Ref($high,1)+Ref($low,1), 0, Greater(Abs($high-Ref($high,1)),Abs($low-Ref($low,1)))), 12)+Sum(If($high+$low<=Ref($high,1)+Ref($low,1), 0, Greater(Abs($high-Ref($high,1)),Abs($low-Ref($low,1)))), 12)+1e-12)',
    "alpha50": '-1*Max(Rank(Corr(Rank($volume,1),Rank($vwap,1),5),1),5)',
    "alpha51": 'Sum(If($high+$low>=Ref($high,1)+Ref($low,1), 0, Greater(Abs($high-Ref($high,1)),Abs($low-Ref($low,1)))), 12)/(Sum(If($high+$low>=Ref($high,1)+Ref($low,1), 0, Greater(Abs($high-Ref($high,1)),Abs($low-Ref($low,1)))), 12)+Sum(If($high+$low<=Ref($high,1)+Ref($low,1), 0, Greater(Abs($high-Ref($high,1)),Abs($low-Ref($low,1)))), 12)+1e-12)',
    "alpha52": 'Sum(Greater($high-Ref(($high+$low+$close)/3,1),0),26)/(Sum(Greater(Ref(($high+$low+$close)/3,1)-$low,0),26)+1e-12)*100',
    "alpha53": 'Mean($close>Ref($close,1), 12)*100',
    "alpha54": '-1*Rank(Std(Abs($close-$open),1)+($close-$open)+Corr($close,$open,10), 1)',
    "alpha55": 'Sum(($close/Ref($close,1)-1)*$volume/Mean($volume,20), 20)',
    "alpha56": '-1*Rank(Sum($close/Ref($close,1)-1,10)/Sum(Sum($close/Ref($close,1)-1,2),3),1)*Rank($close/Ref($close,1)-1,1)',
    "alpha57": 'SMA(($close-Min($low,9))/(Max($high,9)-Min($low,9)+1e-12)*100, 3, 1)',
    "alpha58": 'Mean($close>Ref($close,1), 20)*100',
    "alpha59": 'Sum(If($close>Ref($close,1), $volume, If($close<Ref($close,1), -$volume, 0)), 20)',
    "alpha60": 'Sum((($close-$low)-($high-$close))/($high-$low+1e-12)*$volume, 20)',
    "alpha61": '-1*Rank(Max($vwap-$close,12), 1)',
    "alpha62": '-1*Corr($high, Rank($volume,1), 5)',
    "alpha63": 'SMA(Greater($close-Ref($close,1),0),6,1)/(SMA(Abs($close-Ref($close,1)),6,1)+1e-12)*100',
    "alpha64": 'SMA(Greater($close-Ref($close,1),0),12,1)/(SMA(Abs($close-Ref($close,1)),12,1)+1e-12)*100',
    "alpha65": 'Mean($close,6)/$close',
    "alpha66": '($close-Mean($close,6))/Mean($close,6)*100',
    "alpha67": 'SMA(Greater($close-Ref($close,1),0),24,1)/(SMA(Abs($close-Ref($close,1)),24,1)+1e-12)*100',
    "alpha68": 'SMA((($high+$low)/2-(Ref($high,1)+Ref($low,1))/2)*($high-$low)/($volume+1e-12), 15, 2)',
    "alpha69": 'If(Sum(If($open<=Ref($open,1),0,Greater($high-$open,$open-Ref($open,1))),20)>Sum(If($open>=Ref($open,1),0,Greater($open-$low,$open-Ref($open,1))),20),(Sum(If($open<=Ref($open,1),0,Greater($high-$open,$open-Ref($open,1))),20)-Sum(If($open>=Ref($open,1),0,Greater($open-$low,$open-Ref($open,1))),20))/Sum(If($open<=Ref($open,1),0,Greater($high-$open,$open-Ref($open,1))),20),If(Sum(If($open<=Ref($open,1),0,Greater($high-$open,$open-Ref($open,1))),20)=Sum(If($open>=Ref($open,1),0,Greater($open-$low,$open-Ref($open,1))),20),0,(Sum(If($open<=Ref($open,1),0,Greater($high-$open,$open-Ref($open,1))),20)-Sum(If($open>=Ref($open,1),0,Greater($open-$low,$open-Ref($open,1))),20))/Sum(If($open>=Ref($open,1),0,Greater($open-$low,$open-Ref($open,1))),20)))',
    "alpha70": 'Std(Amount(), 6)',
    "alpha71": '($close-Mean($close,24))/Mean($close,24)*100',
    "alpha72": 'WMA((Max($high,6)-$close)/(Max($high,6)-Min($low,6)+1e-12)*100, 15)',
    "alpha73": '-1*Rank(WMA(Corr($close,$volume,10),16),4)',
    "alpha74": 'Rank(Corr(Sum($low*0.35+$vwap*0.65,20),Sum(Mean($volume,60),20),7),1)',
    "alpha75": 'Mean($close>$open, 50)',
    "alpha76": 'Std(Abs($close/Ref($close,1)-1)/($volume+1e-12),20)/(Mean(Abs($close/Ref($close,1)-1)/($volume+1e-12),20)+1e-12)',
    "alpha77": 'Less(Rank(WMA(($high+$low)/2+$high-($vwap+$high),20),1),Rank(WMA(Corr(($high+$low)/2,Mean($volume,40),3),6),1))',
    "alpha78": '($high+$low+$close)/3*$volume',
    "alpha79": 'SMA(Greater($close-Ref($close,1),0),12,1)/(SMA(Abs($close-Ref($close,1)),12,1)+1e-12)*100',
    "alpha80": '($volume-Ref($volume,1))/Ref($volume,1)*100',
    "alpha81": 'SMA($volume, 10, 1)',
    "alpha82": 'SMA($high,10,1)/(SMA($low,10,1)+1e-12)*100',
    "alpha83": '-1*Rank(Cov(Rank($high,1),Rank($volume,1),5),1)',
    "alpha84": 'Sum(If($close>Ref($close,1), $volume, If($close<Ref($close,1), -$volume, 0)), 20)',
    "alpha85": 'Rank($volume/Mean($volume,20),20)*Rank(-1*Delta($close,7),8)',
    "alpha86": '(Ref($close,20)-Ref($close,10))/10-(Ref($close,10)-$close)/10',
    "alpha87": '-1*Rank(WMA(Delta($vwap,4),7),1)',
    "alpha88": '($close-Ref($close,20))/Ref($close,20)*100',
    "alpha89": '2*SMA($close,13,2)-SMA($close,27,2)',
    "alpha90": '($close-Ref($close,5))/Ref($close,5)*100',
    "alpha91": '-1*Rank(WMA(Delta($close,2),8),1)',
    "alpha92": '-1*Rank(WMA(Corr($high,$volume,5),5),1)',
    "alpha93": '-1*Rank(WMA(Corr(Rank($vwap,1),Rank($volume,1),5),14),4)',
    "alpha94": '-1*Rank(WMA(Corr($close,Mean($volume,60),9),14),1)',
    "alpha95": '-1*Rank(WMA(Corr(Rank($high,1),Rank(Mean($volume,15),1),9),8),1)',
    "alpha96": '-1*Max(Rank(Corr(Rank($vwap,1),Rank($volume,1),5),1),5)',
    "alpha97": 'Std($volume, 10)',
    "alpha98": 'If(Delta(Mean($close,100),100)/Ref($close,100)<=0.05, -1*($close-Min($close,100)), -1*Delta($close,3))',
    "alpha99": '-1*Rank(Cov(Rank($close,1),Rank($volume,1),5),1)',
    "alpha100": 'Std($volume, 20)',
    "alpha101": '($close-$open)/($high-$low+1e-12)*$volume',
    "alpha102": 'SMA(Greater($close-Ref($close,1),0),6,1)/(SMA(Abs($close-Ref($close,1)),6,1)+1e-12)*100',
    "alpha103": '(20-($high-$low)/(Std($close,20)+1e-12))*100',
    "alpha104": '-1*Delta(Corr($high,$volume,5),5)*Rank(Std($close,20),1)',
    "alpha105": '-1*Corr(Rank($open,1),Rank($volume,1),10)',
    "alpha106": 'Delta($close, 20)',
    "alpha107": '(-1*Rank(Delta($open,1),1))*Rank($open-Ref($close,1),1)*Rank(Delta($volume,1),1)',
    "alpha108": 'Sign(Rank($high-Min($high,2),1))*Power(Abs(Rank($high-Min($high,2),1)), Abs(Rank(Corr($vwap,Mean($volume,120),6),1)))',
    "alpha109": 'SMA($high-$low,10,2)/SMA(SMA($high-$low,10,2),10,2)',
    "alpha110": 'Sum(Greater($high-Ref($close,1),0),20)/(Sum(Greater(Ref($close,1)-$low,0),20)+1e-12)*100',
    "alpha111": 'SMA($volume*(($close-$low)-($high-$close))/($high-$low+1e-12),11,2)-SMA($volume*(($close-$low)-($high-$close))/($high-$low+1e-12),4,2)',
    "alpha112": '(Sum(If($close>Ref($close,1),$volume,0),12)-Sum(If($close<Ref($close,1),$volume,0),12))/(Sum(If($close>Ref($close,1),$volume,0),12)+Sum(If($close<Ref($close,1),$volume,0),12)+1e-12)*100',
    "alpha113": '-1*Rank(Sum(Ref($close,5),20)/20,1)*Corr($close,$volume,2)*Rank(Corr(Sum($close,5),Sum($close,20),2),1)',
    "alpha114": 'Rank(Ref(Power(If($close/Ref($close,1)-1<0, Std($close/Ref($close,1)-1,20), $close), 2), 5), 1)',
    "alpha115": '-1*Rank(Corr($high,$volume,30),1)*Rank($high,1)',
    "alpha116": 'Slope($close, 20)/$close',
    "alpha117": 'Rank($volume,32)*(1-Rank($close+$high-$low,16))*(1-Rank($close/Ref($close,1)-1,32))',
    "alpha118": 'Sum($high-$open,20)/(Sum($open-$low,20)+1e-12)*100',
    "alpha119": 'Rank(WMA(Corr($vwap,Sum(Mean($volume,5),26),5),7),1)-Rank(WMA(Rank(TsArgmin(Corr(Rank($open,1),Rank(Mean($volume,15),1),21),9),7),8),1)',
    "alpha120": 'Rank($vwap-$close,1)/Rank($vwap+$close,1)',
    "alpha121": 'Sign(Rank($vwap-Min($vwap,12),1))*Power(Abs(Rank($vwap-Min($vwap,12),1)), Abs(Rank(Corr(Rank($vwap,20),Rank(Mean($volume,60),2),18),3)))',
    "alpha122": 'SMA(SMA(Log($close),13,2)-SMA(Log($close),27,2),2,1)',
    "alpha123": 'Rank(Corr(Sum(($high+$low)/2,20),Sum(Mean($volume,60),20),9),1)*Rank(Corr($low,$volume,6),1)',
    "alpha124": '($close-$vwap)/WMA(Rank(TsArgmax($close,30),1),2)',
    "alpha125": 'Rank(WMA(Corr($vwap,Mean($volume,17),5),6),1)*Rank(WMA(Rank(Corr(Rank($low,1),Rank(Mean($volume,10),1),5),6),2),1)',
    "alpha126": '($close+$high+$low)/3',
    "alpha127": 'Power(Power(100*($close-Max($close,12))/(Max($close,12)+1e-12), 2), 0.5)',
    "alpha128": '100-(100/(1+Sum(If(($high+$low+$close)>Ref(($high+$low+$close),1),Greater($high,Ref($close,1)),Less($low,Ref($close,1))),14)))',
    "alpha129": 'Sum(If($close<Ref($close,1), Abs($close-Ref($close,1)), 0), 12)',
    "alpha130": 'Rank(WMA(Corr(($high+$low)/2,Mean($volume,40),9),10),1)/Rank(WMA(Corr(Rank($vwap,1),Rank($volume,1),7),3),1)',
    "alpha131": 'Sign(Rank(Delta($vwap,1),1))*Power(Abs(Rank(Delta($vwap,1),1)), Abs(Rank(Corr($close,Mean($volume,50),18),18)))',
    "alpha132": 'Mean(Amount(), 20)',
    "alpha133": '(20-($high-$low)/(Std($close,20)+1e-12))*100',
    "alpha134": '($close-Ref($close,12))/Ref($close,12)*$volume',
    "alpha135": 'SMA(Ref($close/Ref($close,20),1),20,1)',
    "alpha136": '-1*Rank(Delta($close/Ref($close,1),3),1)*Corr($open,$volume,10)',
    "alpha137": '-1*Rank(WMA(Delta($close,2),8),1)*Rank(WMA(Corr($vwap,Mean($volume,20),8),6),1)',
    "alpha138": '-1*Rank(WMA(Std($low,10),6),1)*Rank(WMA(Corr($low,Mean($volume,10),10),6),1)',
    "alpha139": '-1*Rank(Delta($close,3),1)*Corr($open,$volume,10)',
    "alpha140": 'Less(Rank(WMA(Rank($open,1)+Rank($low,1)-Rank($high,1)-Rank($close,1),8),1),Rank(WMA(Corr(Rank($close,8),Rank(Mean($volume,60),20),8),7),3))',
    "alpha141": '-1*Rank(Corr(Rank($high,1),Rank(Mean($volume,15),1),9),1)',
    "alpha142": '-1*Rank(Rank($close,10),1)*Rank(Delta(Delta($close,1),1),1)*Rank(Rank($volume/Mean($volume,20),5),1)',
    "alpha143": 'If($close>Ref($close,1), ($close-Ref($close,1))/Ref($close,1), 1/Mean($close,3))',
    "alpha144": 'Sum(If($close<Ref($close,1), Abs($close/Ref($close,1)-1)/(Amount()+1e-12), 0), 20)/(Sum(If($close<Ref($close,1), 1, 0), 20)+1e-12)',
    "alpha145": '(Mean($volume,9)-Mean($volume,26))/Mean($volume,12)*100',
    "alpha146": 'Mean(($close/Ref($close,1)-1-(Mean($close,20)-Ref(Mean($close,20),1))/Ref($close,1)), 60)',
    "alpha147": 'Slope(Mean($close,12), 12)/$close',
    "alpha148": 'Rank(Corr($open,Sum(Mean($volume,60),9),9),1)*Rank($open-$close+$open-Ref($close,1),1)',
    "alpha149": 'Slope(Mean($volume,12), 12)/($volume+1e-12)',
    "alpha150": '($close+$high+$low)/3*$volume',
    "alpha151": 'SMA(Delta($close,20), 20, 1)',
    "alpha152": 'SMA(Mean(Ref(SMA($high-$low,9,1),1),12)-Mean(Ref(SMA($high-$low,9,1),1),26),9,1)',
    "alpha153": '(Mean($close,3)+Mean($close,6)+Mean($close,12)+Mean($close,24))/(4*$close)',
    "alpha154": '($vwap-Min($vwap,16))-Corr($vwap,Mean($volume,180),18)',
    "alpha155": 'SMA($volume,13,2)-SMA($volume,27,2)',
    "alpha156": '-1*Greater(Rank(WMA(Delta($vwap,5),3),1),Rank(WMA(Delta($open*0.85+$high*0.15,2)/($open*0.85+$high*0.15)*100,3),1))',
    "alpha157": 'Less(Rank(Rank(Log(Sum(Min(Rank(Rank(-1*Rank(Delta($close-$open,5),1)),1),1),2),1)),1),5)+Rank(Delta($vwap,1),5)',
    "alpha158": '($high-$low)/$close',
    "alpha159": '-1*Rank($close,1)*Rank(Delta($close,1),1)',
    "alpha160": 'Less(Rank(Rank(WMA(-1*Rank(Delta($close,2),1),8),1),1),5)+Rank(Delta($vwap,1),5)',
    "alpha161": 'Mean(Greater(Greater($high-$low,Abs(Ref($close,1)-$high)),Abs(Ref($close,1)-$low)),12)',
    "alpha162": '(SMA(Greater($close-Ref($close,1),0),12,1)/(SMA(Abs($close-Ref($close,1)),12,1)+1e-12)*100-Min(SMA(Greater($close-Ref($close,1),0),12,1)/(SMA(Abs($close-Ref($close,1)),12,1)+1e-12)*100,12))/(Max(SMA(Greater($close-Ref($close,1),0),12,1)/(SMA(Abs($close-Ref($close,1)),12,1)+1e-12)*100,12)-Min(SMA(Greater($close-Ref($close,1),0),12,1)/(SMA(Abs($close-Ref($close,1)),12,1)+1e-12)*100,12)+1e-12)',
    "alpha163": 'Rank(Power(If($close>Ref($close,1), Std($close,20), 0), 2), 1)',
    "alpha164": 'SMA(If($close>Ref($close,1), 1/($close-Ref($close,1)+1e-12), 1-Less(1,Abs($close-Ref($close,1)))), 12, 1)/($high-$low+1e-12)*100',
    "alpha165": 'Max($close/Mean($volume,20), 60)/(Min($close/Mean($volume,20), 60)+1e-12)',
    "alpha166": '-20*Power(19,1.5)*Sum($close/Ref($close,1)-1-Mean($close/Ref($close,1)-1,20),20)/(19*18*Power(Sum(Power($close/Ref($close,1)-1,2),20),1.5)+1e-12)',
    "alpha167": 'Sum(Greater($close-Ref($close,1),0), 12)',
    "alpha168": '-1*$volume/Mean($volume,20)',
    "alpha169": 'SMA(Mean(Ref(SMA($close-Ref($close,1),9,1),1),12)-Mean(Ref(SMA($close-Ref($close,1),9,1),1),26),9,1)',
    "alpha170": 'Rank(($close/Ref($close,1)-1)*$volume,1)*Rank($vwap-Max($vwap,12),16)',
    "alpha171": '-1*Rank($low,1)*Rank($open,1)*Rank($high,1)*Rank($close,1)',
    "alpha172": 'Mean(Abs(Sum(Log($close/Ref($close,1)),6)/6-Log($close/Ref($close,20))/20),15)',
    "alpha173": '3*SMA($close,13,2)-2*SMA(SMA($close,13,2),3,1)',
    "alpha174": 'SMA(If($close<Ref($close,1), Std($close,20), 0), 20, 1)',
    "alpha175": 'Mean(Greater(Greater($high-$low,Abs(Ref($close,1)-$high)),Abs(Ref($close,1)-$low)),6)',
    "alpha176": 'Corr(Rank(($close-Min($low,12))/(Max($high,12)-Min($low,12)+1e-12),1),Rank($volume,1),6)',
    "alpha177": '(20-($high-$low)/(Std($close,20)+1e-12))*100',
    "alpha178": '($close-Ref($close,1))/Ref($close,1)*$volume',
    "alpha179": 'Rank(Corr($vwap,$volume,4),1)*Rank(Corr(Rank($low,1),Rank(Mean($volume,50),1),12),1)',
    "alpha180": 'Mean($volume,7)/Mean($volume,20)',
    "alpha181": 'Sum(If($close>Ref($close,1), $volume, 0), 20)/Mean($volume,20)',
    "alpha182": 'Mean($close>Ref($close,1), 20)*100',
    "alpha183": 'Mean($close>Ref($close,1), 20)*100',
    "alpha184": 'Rank(Corr(Ref($open-$close,1),$close,200),1)+Rank($open-$close,1)',
    "alpha185": '-1*Rank(Abs($close-Ref($close,1)),1)*Corr($close,$volume,10)',
    "alpha186": 'Mean($low-Ref($low,1),20)+Mean($high-Ref($high,1),20)',
    "alpha187": 'Sum(If($open>Ref($open,1), 0, Greater($open-Ref($open,1),Abs($open-Ref($open,1)))), 20)',
    "alpha188": '($high-$low-SMA($high-$low,11,2))/(SMA($high-$low,11,2)+1e-12)*100',
    "alpha189": 'Mean(Abs($close-Mean($close,6)),6)',
    "alpha190": 'Log((Mean($close/Ref($close,1)-1>0,20)+1e-12)/(Mean($close/Ref($close,1)-1<0,20)+1e-12))',
    "alpha191": 'Rank(Corr(Mean($volume,20),$low,5)+(($high+$low)/2)-$close, 1)',
}

IMPLEMENTED_GTJA191_FACTORS = tuple(f"alpha{i}" for i in range(1, 192))


def compute_gtja191_alphas(df: pd.DataFrame, factor_names: list[str] | None = None) -> pd.DataFrame:
    """计算 GTJA191 因子（默认全部 191 个）。

    Parameters
    ----------
    df : pd.DataFrame
        长表面板，需含列 date, code, open, high, low, close, volume（可选 vwap）。
    factor_names : list[str] | None
        指定因子名；默认全部 191 个。

    Returns
    -------
    pd.DataFrame
        含 date, code 与各因子列的面板。
    """
    data = sort_panel(df)
    requested = list(factor_names or IMPLEMENTED_GTJA191_FACTORS)
    invalid = [n for n in requested if n not in GTJA_EXPRESSIONS]
    if invalid:
        raise ValueError(f"Unsupported GTJA191 factors: {invalid}")

    result = data[["date", "code"]].copy()
    # 用 dict 收集后一次性 concat，避免逐列赋值触发的 DataFrame fragmentation 警告
    cols: dict[str, pd.Series] = {}
    for fname in requested:
        try:
            val = evaluate(GTJA_EXPRESSIONS[fname], data)
        except Exception as exc:  # 单因子失败时给出因子名，便于定位
            raise RuntimeError(f"GTJA191 factor {fname} failed: {exc}") from exc
        if not isinstance(val, pd.Series):
            val = pd.Series(val, index=data.index)
        cols[fname] = val.replace([np.inf, -np.inf], np.nan)
    if cols:
        result = pd.concat([result, pd.DataFrame(cols, index=data.index)], axis=1)
    return result


def get_factor_names() -> list[str]:
    """返回全部 191 个因子名。"""
    return list(IMPLEMENTED_GTJA191_FACTORS)


def get_factor_formula(name: str) -> str:
    """返回单个因子的 qlib 公式源码。"""
    return GTJA_EXPRESSIONS.get(name, "")


__all__ = [
    "GTJA_EXPRESSIONS",
    "IMPLEMENTED_GTJA191_FACTORS",
    "compute_gtja191_alphas",
    "get_factor_names",
    "get_factor_formula",
]
