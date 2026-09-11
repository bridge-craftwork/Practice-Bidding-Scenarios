# GIB report: Drury

Match: 483/500 = 96.6%

- Capture: `GIB/Drury.pbn` (500 boards; robots: BasicGIB 2/1)
- Filter: `Auction.....\nPass Pass 1[HS] Pass 2C`
- Matched: `GIB-filtered/Drury.pdf`
- Not matched: `GIB-filtered-out/Drury.pdf` (board numbers below are this file's)

## Not matched: 17 boards, by sequence

```
    2  P-P-1H-P-3D-P-4H
    2  P-P-1S-P-1N-P-2H
    2  P-P-1S-P-2D-P-3H-P-4H
    2  P-P-1S-P-3D-P-4S
    1  P-P-1C-P-1H-P-2S-P-2N-P-3C-P-3D-P-3S-P-4N-P-5H-P-5S
    1  P-P-1D-P-1H-P-1S-P-1N-P-2D-P-2S
    1  P-P-1D-P-1N-P-2H-P-3D-P-3N
    1  P-P-1H-P-2D-P-2S-P-2N-P-3H-P-3N-P-4S
    1  P-P-1S-P-1N-P-2H-P-2S-P-3N
    1  P-P-1S-P-1N-P-2H-P-2S-P-4H
    1  P-P-1S-P-1N-P-2H-P-2S-P-4S
    1  P-P-1S-P-1N-P-3H-P-3N-P-4H
    1  P-P-1S-P-1N-P-3H-P-4H
```

## Matched: 483 boards, by sequence

```
  219  P-P-1H-P-2C-P-4H
  202  P-P-1S-P-2C-P-4S
   15  P-P-1H-P-2C-P-2D-P-2H
   10  P-P-1S-P-2C-P-2D-P-2S
    4  P-P-1H-P-2C-P-3S-P-4H
    4  P-P-1S-P-2C-P-3S-P-4S
    3  P-P-1H-P-2C-P-3H-P-4H
    3  P-P-1S-P-2C-P-2D-P-3S-P-4S
    2  P-P-1H-P-2C-P-2H
    2  P-P-1S-P-2C-P-3D-P-4D-P-4S
    2  P-P-1S-P-2C-P-3H-P-4S
    1  P-P-1H-P-2C-P-2D-P-2H-P-4H
    1  P-P-1H-P-2C-P-2D-P-4H
    1  P-P-1H-P-2C-P-2S-P-4H
    1  P-P-1H-P-2C-P-3H-P-4H-P-5C-P-6H
    1  P-P-1H-P-2C-P-3H-P-4H-P-6H
    1  P-P-1H-P-2C-P-3S-P-4H-P-4N-P-5D-P-6H
    1  P-P-1S-P-2C-P-2D-P-2H-P-2S
    1  P-P-1S-P-2C-P-2D-P-2S-P-4S
    1  P-P-1S-P-2C-P-2D-P-4S
    1  P-P-1S-P-2C-P-2S
    1  P-P-1S-P-2C-P-3D-P-3N-P-4S
    1  P-P-1S-P-2C-P-3D-P-4D-P-6S
    1  P-P-1S-P-2C-P-3D-P-4S
    1  P-P-1S-P-2C-P-3H-P-3N-P-4S
    1  P-P-1S-P-2C-P-3H-P-4H-P-4N-P-5H-P-5N-P-6S
    1  P-P-1S-P-2C-P-3S-P-4C-P-4N-P-5S-P-5N-P-6S
    1  P-P-1S-P-2C-P-3S-P-4S-P-5C-P-6S
```

## Not matched: example deals

### P-P-1H-P-3D-P-4H (2)

```
[Event "autoCapture"]
[Board "6"]
[West "BasicGIB 2/1"]
[North "BasicGIB 2/1"]
[East "BasicGIB 2/1"]
[South "BasicGIB 2/1"]
[Dealer "S"]
[Vulnerable "None"]
[Deal "N:AQ.AJ642.84.A943 KT4.53.A976.KT62 653.KQ98.KJ532.J J9872.T7.QT.Q875"]
{Shape 2524 3244 3451 5224}
{HCP 15 10 10 5}
{TP 16 11 11 6}
{Losers 7 8 7 9}
[Contract "4H"]
[Declarer "N"]
[Auction "S"]
Pass    Pass    1H      Pass
3D      Pass    4H      Pass
Pass    Pass

[Event "autoCapture"]
[Board "12"]
[West "BasicGIB 2/1"]
[North "BasicGIB 2/1"]
[East "BasicGIB 2/1"]
[South "BasicGIB 2/1"]
[Dealer "S"]
[Vulnerable "EW"]
[Deal "N:AK94.AJ652.K87.Q QT63.4.T95.KT732 8.KQ83.A6432.865 J752.T97.QJ.AJ94"]
{Shape 4531 4135 1453 4324}
{HCP 17 5 9 9}
{TP 18 7 11 9}
{Losers 6 8 7 10}
[Contract "4H"]
[Declarer "N"]
[Auction "S"]
Pass    Pass    1H      Pass
3D      Pass    4H      Pass
Pass    Pass
```

### P-P-1S-P-1N-P-2H (2)

```
[Event "autoCapture"]
[Board "5"]
[West "BasicGIB 2/1"]
[North "BasicGIB 2/1"]
[East "BasicGIB 2/1"]
[South "BasicGIB 2/1"]
[Dealer "S"]
[Vulnerable "NS"]
[Deal "N:AQT74.T8743.Q.AK J985.K9.A653.Q43 6.QJ2.KJ42.JT976 K32.A65.T987.852"]
{Shape 5512 4243 1345 3343}
{HCP 15 10 8 7}
{TP 16 10 10 7}
{Losers 5 8 8 10}
[Contract "2H"]
[Declarer "N"]
[Auction "S"]
Pass    Pass    1S      Pass
1N     Pass    2H      Pass
Pass    Pass

[Event "autoCapture"]
[Board "10"]
[West "BasicGIB 2/1"]
[North "BasicGIB 2/1"]
[East "BasicGIB 2/1"]
[South "BasicGIB 2/1"]
[Dealer "S"]
[Vulnerable "All"]
[Deal "N:AJ962.AQ632.4.KJ Q853.T985.AKJ.95 T.KJ4.9862.AT872 K74.7.QT753.Q643"]
{Shape 5512 4432 1345 3154}
{HCP 15 10 8 7}
{TP 17 11 10 9}
{Losers 5 8 8 7}
[Contract "2H"]
[Declarer "N"]
[Auction "S"]
Pass    Pass    1S      Pass
1N     Pass    2H      Pass
Pass    Pass
```

### P-P-1S-P-2D-P-3H-P-4H (2)

```
[Event "autoCapture"]
[Board "13"]
[West "BasicGIB 2/1"]
[North "BasicGIB 2/1"]
[East "BasicGIB 2/1"]
[South "BasicGIB 2/1"]
[Dealer "S"]
[Vulnerable "EW"]
[Deal "N:AQJ92.AQ982.K.53 K43.J5.J874.KJT2 8.KT64.T9632.AQ9 T765.73.AQ5.8764"]
{Shape 5512 3244 1453 4234}
{HCP 16 9 9 6}
{TP 18 9 11 7}
{Losers 5 9 7 9}
[Contract "4H"]
[Declarer "N"]
[Auction "S"]
Pass    Pass    1S      Pass
2D      Pass    3H      Pass
4H      Pass    Pass    Pass

[Event "autoCapture"]
[Board "14"]
[West "BasicGIB 2/1"]
[North "BasicGIB 2/1"]
[East "BasicGIB 2/1"]
[South "BasicGIB 2/1"]
[Dealer "S"]
[Vulnerable "None"]
[Deal "N:KQT92.AQ543.A4.9 J754.T2.Q52.A864 A.K87.K9763.T752 863.J96.JT8.KQJ3"]
{Shape 5521 4234 1354 3334}
{HCP 15 7 10 8}
{TP 17 8 11 8}
{Losers 4 9 7 10}
[Contract "4H"]
[Declarer "N"]
[Auction "S"]
Pass    Pass    1S      Pass
2D      Pass    3H      Pass
4H      Pass    Pass    Pass
```

### P-P-1S-P-3D-P-4S (2)

```
[Event "autoCapture"]
[Board "1"]
[West "BasicGIB 2/1"]
[North "BasicGIB 2/1"]
[East "BasicGIB 2/1"]
[South "BasicGIB 2/1"]
[Dealer "S"]
[Vulnerable "None"]
[Deal "N:AKT82.Q9.AT.Q976 943.JT72.92.AK85 QJ65.K5.KJ654.43 7.A8643.Q873.JT2"]
{Shape 5224 3424 4252 1543}
{HCP 15 8 10 7}
{TP 15 9 11 9}
{Losers 6 9 7 8}
[Contract "4S"]
[Declarer "N"]
[Auction "S"]
Pass    Pass    1S      Pass
3D      Pass    4S      Pass
Pass    Pass

[Event "autoCapture"]
[Board "17"]
[West "BasicGIB 2/1"]
[North "BasicGIB 2/1"]
[East "BasicGIB 2/1"]
[South "BasicGIB 2/1"]
[Dealer "S"]
[Vulnerable "EW"]
[Deal "N:AK653.QT87.3.A63 Q8.J432.KJ85.JT2 JT72.K.AQT97.974 94.A965.642.KQ85"]
{Shape 5413 2443 4153 2434}
{HCP 13 8 10 9}
{TP 15 8 11 10}
{Losers 6 10 8 8}
[Contract "4S"]
[Declarer "N"]
[Auction "S"]
Pass    Pass    1S      Pass
3D      Pass    4S      Pass
Pass    Pass
```

### P-P-1C-P-1H-P-2S-P-2N-P-3C-P-3D-P-3S-P-4N-P-5H-P-5S (1)

```
[Event "autoCapture"]
[Board "7"]
[West "BasicGIB 2/1"]
[North "BasicGIB 2/1"]
[East "BasicGIB 2/1"]
[South "BasicGIB 2/1"]
[Dealer "S"]
[Vulnerable "All"]
[Deal "N:KJ943.K..AKQJ932 AT7.J842.QJ4.654 652.AT76.AT982.T Q8.Q953.K7653.87"]
{Shape 5107 3433 3451 2452}
{HCP 17 8 8 7}
{TP 21 8 10 8}
{Losers 3 10 8 8}
[Contract "5S"]
[Declarer "N"]
[Auction "S"]
Pass    Pass    1C      Pass
1H      Pass    2S      Pass
2N     Pass    3C      Pass
3D      Pass    3S      Pass
4N     Pass    5H      Pass
5S      Pass    Pass    Pass
```

### P-P-1D-P-1H-P-1S-P-1N-P-2D-P-2S (1)

```
[Event "autoCapture"]
[Board "2"]
[West "BasicGIB 2/1"]
[North "BasicGIB 2/1"]
[East "BasicGIB 2/1"]
[South "BasicGIB 2/1"]
[Dealer "S"]
[Vulnerable "None"]
[Deal "N:K9742.4.AKT932.K QJT.K973.J86.QJ9 653.QJT6.Q.AT752 A8.A852.754.8643"]
{Shape 5161 3433 3415 2434}
{HCP 13 10 9 8}
{TP 16 10 10 8}
{Losers 5 9 8 9}
[Contract "2S"]
[Declarer "N"]
[Auction "S"]
Pass    Pass    1D      Pass
1H      Pass    1S      Pass
1N     Pass    2D      Pass
2S      Pass    Pass    Pass
```

### P-P-1D-P-1N-P-2H-P-3D-P-3N (1)

```
[Event "autoCapture"]
[Board "4"]
[West "BasicGIB 2/1"]
[North "BasicGIB 2/1"]
[East "BasicGIB 2/1"]
[South "BasicGIB 2/1"]
[Dealer "S"]
[Vulnerable "All"]
[Deal "N:Q.QJT73.AKQT72.K JT874.A42.8.8765 A53.K95.J93.QT43 K962.86.654.AJ92"]
{Shape 1561 5314 3334 4234}
{HCP 17 5 10 8}
{TP 19 7 10 9}
{Losers 4 9 9 9}
[Contract "3N"]
[Declarer "S"]
[Auction "S"]
Pass    Pass    1D      Pass
1N     Pass    2H      Pass
3D      Pass    3N     Pass
Pass    Pass
```

### P-P-1H-P-2D-P-2S-P-2N-P-3H-P-3N-P-4S (1)

```
[Event "autoCapture"]
[Board "9"]
[West "BasicGIB 2/1"]
[North "BasicGIB 2/1"]
[East "BasicGIB 2/1"]
[South "BasicGIB 2/1"]
[Dealer "S"]
[Vulnerable "EW"]
[Deal "N:AJ854.AQJT63.K.5 QT6.972.AT4.JT86 973.5.QJ987.AQ42 K2.K84.6532.K973"]
{Shape 5611 3334 3154 2344}
{HCP 15 7 9 9}
{TP 18 7 11 9}
{Losers 5 10 7 8}
[Contract "4S"]
[Declarer "N"]
[Auction "S"]
Pass    Pass    1H      Pass
2D      Pass    2S      Pass
2N     Pass    3H      Pass
3N     Pass    4S      Pass
Pass    Pass
```

### P-P-1S-P-1N-P-2H-P-2S-P-3N (1)

```
[Event "autoCapture"]
[Board "3"]
[West "BasicGIB 2/1"]
[North "BasicGIB 2/1"]
[East "BasicGIB 2/1"]
[South "BasicGIB 2/1"]
[Dealer "S"]
[Vulnerable "EW"]
[Deal "N:AKQ63.Q8754.A.J9 875.A962.QJ8.876 J4.KJ3.76543.KQT T92.T.KT92.A5432"]
{Shape 5512 3433 2353 3145}
{HCP 16 7 10 7}
{TP 17 7 10 9}
{Losers 4 10 8 8}
[Contract "3N"]
[Declarer "S"]
[Auction "S"]
Pass    Pass    1S      Pass
1N     Pass    2H      Pass
2S      Pass    3N     Pass
Pass    Pass
```

### P-P-1S-P-1N-P-2H-P-2S-P-4H (1)

```
[Event "autoCapture"]
[Board "8"]
[West "BasicGIB 2/1"]
[North "BasicGIB 2/1"]
[East "BasicGIB 2/1"]
[South "BasicGIB 2/1"]
[Dealer "S"]
[Vulnerable "NS"]
[Deal "N:K7432.AQJ98.AJ8. T65.K63.Q75.QT94 A8.742.K92.K7652 QJ9.T5.T643.AJ83"]
{Shape 5530 3334 2335 3244}
{HCP 15 7 10 8}
{TP 18 7 10 9}
{Losers 5 9 8 9}
[Contract "4H"]
[Declarer "N"]
[Auction "S"]
Pass    Pass    1S      Pass
1N     Pass    2H      Pass
2S      Pass    4H      Pass
Pass    Pass
```

...and 3 more sequences; see GIB-filtered-out/Drury.pdf
