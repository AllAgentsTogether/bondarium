<?php
/**
 * Täglicher Besucherbericht (seit 01.10.2026, docs/STATISTIK.md): liest die Tageswerte von aufruf.php, zeichnet daraus
 * ein PDF (A4, eine Seite, Gestaltung wie der Depot-Auszug: Helvetica, grünes Band mit Logo) und schickt es per E-Mail
 * an BERICHT_AN. Wird nur von aufruf.php geladen; direkt aufgerufen antwortet die Datei mit 404 (zusätzlich per
 * .htaccess gesperrt).
 *
 * Teile: Pdf – kleiner PDF-Schreiber, PHP-Fassung von pdf.js (gleiche Maße: Punkt, Ursprung oben links, Farben 0–1
 * oder „#RRGGBB“, Helvetica in WinAnsi) · bericht_pdf() – die Seite · bericht_daten() – Zahlen aus der Datenbank ·
 * bericht_senden() – E-Mail mit Anhang (lokal: Dateien in statistik-daten/).
 */
declare(strict_types=1);

if (realpath($_SERVER['SCRIPT_FILENAME'] ?? '') === __FILE__) { http_response_code(404); exit; }

// Wortmarke „bondarium“ aus der Kopfzeile der Website (.brand-w, viewBox 0 0 1303 210 – Logo 06, Pixelmaß der Reinzeichnung)
const BERICHT_WORTMARKE = 'M0.9 18L4 17.4L30 17.1L42 17.4L42.6 18L43.2 25L43.3 81L44 83C48 80.3 52.2 76.8 56 74.8C59.8 72.7 63 71.7 67 70.7C71 69.6 75.5 68.7 80 68.4C84.5 68.2 88.8 68.2 94 68.9C99.2 69.6 106.2 71.1 111 72.8C115.8 74.4 119.2 76.3 123 78.6C126.8 80.9 130.3 83.2 134 86.6C137.7 90 142 94.8 145 99C148.1 103.2 150.2 107.2 152.1 112C154 116.8 155.5 123.7 156.3 128C157.1 132.3 157 134.7 157 138C157.1 141.3 156.9 145.2 156.6 148C156.4 150.8 156.3 152 155.5 155C154.8 158 153.8 162.5 152.4 166C151 169.5 149.9 172.2 147.2 176C144.6 179.8 139.8 185.6 136.6 189C133.4 192.4 130.8 194.2 128 196.2C125.2 198.2 122.8 199.6 120 201.1C117.2 202.6 114.5 204 111 205.2C107.5 206.4 102.3 207.7 99 208.5C95.7 209.2 94.5 209.4 91 209.6C87.5 209.8 82.5 210 78 209.5C73.5 208.9 68.5 208 64 206.3C59.5 204.6 54.7 201.8 51 199.5C47.3 197.3 45 195 42 192.8C41.7 196.8 41.5 202.7 41.2 205C40.9 207.3 40.4 205.9 40 206.4L8 206.5L0.9 206L0.9 18ZM575.8 18L577 17.4L599 17.2C604.7 17.2 612.9 17.2 616 17.4C619.1 17.5 617.2 17.8 617.8 18L618.3 41L618.1 206L617 206.6L578 206.2L577 194.2C573 197.2 568.2 201.1 565 203.1C561.8 205.2 560.8 205.4 558 206.4C555.2 207.4 552.5 208.6 548 209.2C543.5 209.7 536.2 210 531 209.6C525.8 209.1 521.3 207.8 517 206.3C512.7 204.8 508.5 202.4 505 200.3C501.5 198.3 499 196.7 496 193.9C493 191.2 489.5 187.5 486.8 184C484.1 180.5 481.8 177 479.8 173C477.8 169 476 164.2 474.8 160C473.6 155.8 472.9 152.7 472.5 148C472.1 143.3 472.2 136.2 472.4 132C472.6 127.8 473.2 125.7 473.7 123C474.3 120.3 474.6 119 475.6 116C476.6 113 478.5 108 479.9 105C481.3 102 481.6 101 483.8 98C486.1 95 490.3 90 493.3 87C496.4 84 499.1 81.8 502 79.7C504.9 77.6 508.5 75.7 511 74.4C513.5 73.1 513.8 72.8 517 71.8C520.2 70.9 526 69.3 530 68.7C534 68.1 538 68.1 541 68.1C544 68.2 544.7 68 548 68.8C551.3 69.5 556.5 70.6 561 72.5C565.5 74.4 570.3 77.7 575 80.4L575.7 77L575.8 18ZM229.1 69C233.5 68.3 235.4 68.4 239 68.3C242.6 68.3 248 68.5 251 68.8C254 69 253.2 68.7 257 69.7C260.8 70.7 269.5 73 274 74.7C278.5 76.3 280.5 77.5 284 79.7C287.5 81.9 291.7 85 295 87.9C298.3 90.8 301.3 93.9 304 97.2C306.7 100.6 309.2 103.9 311.2 108C313.3 112.1 315.1 117.5 316.3 122C317.5 126.5 318.1 130.3 318.3 135C318.5 139.7 318.2 145.3 317.5 150C316.8 154.7 316 158.7 314.3 163C312.6 167.3 310 171.9 307.3 176C304.6 180.1 301.4 183.9 298 187.3C294.6 190.7 291 193.7 287 196.3C283 199 278.3 201.4 274 203.2C269.7 205.1 265.3 206.4 261 207.5C256.7 208.5 252.3 208.9 248 209.6L230 209.3C225 208.2 219.8 207.6 215 206.1C210.2 204.5 205.5 202.6 201 200.1C196.5 197.6 191.9 194.2 188.2 191C184.4 187.8 181.4 184.5 178.7 181C175.9 177.5 173.7 174 171.7 170C169.7 166 167.9 161.7 166.7 157C165.6 152.3 165 146 164.7 142C164.4 138 164.5 136 164.8 133C165 130 165.2 127.7 166 124C166.9 120.3 168 115.3 170 111C171.9 106.7 174.4 102.2 177.6 98C180.8 93.8 185.4 89.4 189.3 86C193.2 82.6 197.1 80.1 201 77.9C204.9 75.7 208.3 74.1 213 72.7C217.7 71.2 224.8 69.7 229.1 69ZM397.4 69C400.9 68.3 402.2 68.4 405 68.4C407.8 68.3 410.8 68.2 414 68.6C417.2 69 421.3 70 424 70.7C426.7 71.4 427.5 71.6 430 72.7C432.5 73.8 436.3 75.8 439 77.5C441.7 79.2 443.7 80.6 446 82.7C448.3 84.8 450.7 87.6 452.5 90C454.4 92.4 455.5 94 457 97C458.5 100 460.3 103.8 461.3 108C462.4 112.2 462.6 117.3 463.3 122L463 206C462.7 206.2 463 206.5 462 206.6C461 206.7 458.7 206.6 457 206.6L425 206.6L421.8 206L421.5 132C421.2 129 421 125.5 420.4 123C419.9 120.5 419.4 119.1 418.2 117C417 114.9 415 112.3 413 110.6C411 108.8 408 107.5 406 106.6C404 105.7 402.7 105.6 401 105.3C399.3 105 398.3 104.7 396 105C393.7 105.2 389.8 105.7 387 106.7C384.2 107.7 381.2 109.3 379 111C376.8 112.7 375.1 114.7 373.6 117C372.1 119.3 370.6 122.5 369.8 125C369 127.5 369 129.7 368.6 132L368.3 206L367 206.7L328 206.5L327.1 205L327.3 72L331 71.3L365 71.4L365.8 72C366.1 75.7 366.3 81 366.5 83C366.6 85 366.8 83.7 367 84C368.7 82.6 369.2 81.6 372 79.7C374.8 77.9 379.8 74.6 384 72.8C388.2 71 393.9 69.7 397.4 69ZM683.1 69C687.2 68.3 687.2 68.4 691 68.3C694.8 68.2 701.3 68.2 706 68.6C710.7 69 715.7 70.1 719 70.8C722.3 71.5 722.7 71.4 726 72.8C729.3 74.1 736.2 77.4 739 78.9C741.8 80.4 741 79.9 743 81.8C745 83.6 749 87.5 751.2 90C753.4 92.5 754.6 94 756.1 97C757.7 100 759.3 104 760.4 108C761.5 112 761.8 116.7 762.5 121L762.5 205L762 206.5L725 206.3L723.7 205L723.2 195L722 194.4C720.7 195.7 719.6 197 718 198.2C716.4 199.5 714.6 200.8 712.6 202C710.6 203.2 708.1 204.4 706 205.3C703.9 206.2 703.5 206.6 700 207.3C696.5 208 689.5 209.4 685 209.7C680.5 210.1 677.3 210 673 209.4C668.7 208.9 663.3 208 659 206.4C654.7 204.9 649.9 201.9 647 200.2C644.1 198.5 643.8 198.4 641.6 196C639.4 193.6 635.5 188.5 633.8 186C632.2 183.5 632.4 183.2 631.7 181C631 178.8 629.9 176.5 629.6 173C629.3 169.5 629.7 162.8 629.9 160C630.1 157.2 630.1 158.2 630.9 156C631.7 153.8 633.4 149.4 634.8 147C636.1 144.6 637.3 143.4 639 141.7C640.7 140 643.2 138.1 645 136.8C646.8 135.4 647.7 134.8 650 133.6C652.3 132.4 655.2 130.8 659 129.6C662.8 128.4 667.8 127.2 673 126.4C678.2 125.6 684.3 125.4 690 125L717 125.1C718 125.1 719.3 125.1 720 124.9C720.7 124.7 720.9 124.3 721.4 124C721.4 122 721.8 120 721.4 118C721 116 720.2 113.9 719 112C717.8 110.1 716 108.2 714 106.7C712 105.2 710 104 707 103.1C704 102.2 698.8 101.6 696 101.4C693.2 101.1 692.3 101.3 690 101.6C687.7 101.9 685.2 102 682 103C678.8 104.1 674.5 105.7 671 107.8C667.5 110 662.8 114.5 661 115.9C659.2 117.2 660.3 115.9 660 115.9L643 104.4L636.4 99C636.8 97.7 636.6 97 637.7 95C638.7 93 641.2 88.9 642.6 87C644 85.1 644.8 84.6 646 83.5C647.2 82.5 647.8 82.1 650 80.7C652.2 79.4 656.3 76.8 659 75.5C661.7 74.1 662 73.7 666 72.7C670 71.6 678.9 69.7 683.1 69ZM1157.5 69C1161.5 68.5 1167.6 68.4 1171 68.5C1174.4 68.6 1175.8 69.2 1178 69.7C1180.2 70.2 1182 70.8 1184 71.6C1186 72.5 1188 73.4 1190 74.6C1192 75.8 1194 77.2 1196 78.8C1198 80.3 1200.5 82.5 1202 84.1C1203.5 85.6 1204 86.8 1205 88.2C1205.3 88.1 1204.7 89.1 1206 87.9C1207.3 86.7 1210.3 83 1213 80.9C1215.7 78.7 1218.3 76.6 1222 74.8C1225.7 72.9 1231.3 70.9 1235 69.9C1238.7 68.9 1240.7 68.8 1244 68.6C1247.3 68.3 1251.2 68.2 1255 68.5C1258.8 68.9 1263.2 69.7 1267 70.8C1270.8 72 1274.7 73.6 1278 75.4C1281.3 77.3 1284.6 79.9 1287 82C1289.4 84.1 1290.6 85.5 1292.4 88C1294.1 90.5 1296.3 94.7 1297.5 97C1298.6 99.3 1298.7 99.7 1299.4 102C1300 104.3 1300.9 107 1301.4 111C1301.9 115 1302.1 121 1302.5 126L1302 206L1282 206.6L1263 206.5L1261.4 206L1261.4 135C1261.2 132.3 1261.4 129.8 1260.7 127C1260 124.2 1258.6 120.3 1257.3 118C1256.1 115.7 1255 114.4 1253.5 113C1251.9 111.6 1250.2 110.5 1248 109.7C1245.8 108.9 1242.5 108.4 1240 108.2C1237.5 108 1235.5 108 1233 108.7C1230.5 109.5 1227.1 111.1 1225 112.6C1222.9 114.2 1221.7 115.8 1220.4 118C1219.2 120.2 1218.2 123 1217.4 126C1216.7 129 1216.6 132.7 1216.1 136L1215.6 206L1214 206.6L1179 206.6L1174.4 206L1174.2 135C1173.9 132 1173.8 128.7 1173.3 126C1172.8 123.3 1172.2 121.2 1171 119C1169.8 116.8 1167.3 114.1 1166 112.7C1164.7 111.3 1164.3 111.3 1163 110.6C1161.7 110 1159.8 109.1 1158 108.7C1156.2 108.2 1154.5 107.7 1152 107.9C1149.5 108 1145.7 108.6 1143 109.5C1140.3 110.5 1137.8 112.2 1136 113.7C1134.2 115.3 1133.1 116.6 1131.9 119C1130.7 121.4 1129.4 125.2 1128.8 128C1128.1 130.8 1128.2 133.3 1127.9 136L1127.4 206L1125 206.6L1089 206.6L1086.1 206L1085.7 90L1086.3 72L1095 71.3L1126 71.5L1127 86.3C1128.3 84.8 1128.7 83.8 1131 81.8C1133.3 79.9 1138.3 76.3 1141 74.6C1143.7 72.9 1144.2 72.5 1147 71.6C1149.8 70.7 1153.5 69.5 1157.5 69ZM854.8 70C857.6 69.7 859.8 69.7 862 69.9C864.2 70.1 866.1 70.6 868.1 71L868.3 109L867 109.7L849 109.7C846 110.3 842.5 110.8 840 111.6C837.5 112.5 835.7 113.8 834 114.9C832.3 115.9 831.5 116.6 830.1 118C828.7 119.4 826.9 121.3 825.7 123C824.4 124.7 823.4 126.3 822.6 128C821.7 129.7 821.2 130.7 820.6 133C820 135.3 819.5 139 819 142L818.7 206L817 206.6L778 206.6L777.5 206L777.3 201L777.4 72L778 71.1L779 71.1L815 71.5C815.2 72 815.5 69.9 815.6 73C815.8 76.1 815.9 87 816 90C816.1 93 816.1 90.7 816.1 91L817 91.3C819.7 88.4 822 85.2 825 82.6C828 80 831.7 77.5 835 75.7C838.3 73.9 841.7 72.8 845 71.8C848.3 70.9 851.9 70.3 854.8 70ZM969.5 71C971.7 71.1 974.7 71 976 71.2C977.3 71.3 976.9 71.7 977.4 72L977.5 146C977.9 149.3 978 153.2 978.7 156C979.4 158.8 980.5 161.1 981.6 163C982.6 164.9 983.1 165.7 985 167.1C986.9 168.5 990.5 170.3 993 171.3C995.5 172.2 998 172.5 1000 172.7C1002 172.9 1003.5 172.8 1005 172.6C1006.5 172.4 1006.8 172.5 1009 171.5C1011.2 170.5 1015.5 168.4 1018 166.5C1020.5 164.6 1022.4 162.6 1024 160C1025.7 157.4 1027.2 153.7 1028 151C1028.9 148.3 1028.8 146.3 1029.2 144L1029.4 72L1030 71.5L1046 71.2L1069 71.3L1070.6 72L1070.8 205L1070 206.5L1031 206.3C1030.7 205.9 1030.4 206.9 1030.2 205C1030.1 203.1 1030.1 198.3 1030 195L1029 194.2C1026.3 196.2 1024.3 198.1 1021 200.2C1017.7 202.2 1012.2 205.1 1009 206.5C1005.8 207.9 1004.5 207.9 1002 208.4C999.5 208.9 997.5 209.5 994 209.6C990.5 209.8 985 209.7 981 209.3C977 208.9 973.3 208.2 970 207.2C966.7 206.2 963.8 204.6 961 203.1C958.2 201.6 956 200.4 953.2 198C950.5 195.6 946.6 191.3 944.6 189C942.7 186.7 942.6 186 941.6 184C940.5 182 939.4 179.3 938.6 177C937.8 174.7 937.1 172.3 936.7 170C936.2 167.7 936.1 165.3 935.8 163L935 72L937 71.1L969.5 71ZM877.5 72L878 71.3L884 71.1L917 71.2L919.6 72L919.9 190C919.8 195 919.9 202.3 919.7 205C919.6 207.7 919.2 206 919 206.5L882 206.6L877.8 206L877.5 72ZM76 105C72.7 105.1 69.3 106.1 67 106.7C64.7 107.3 63.8 107.8 62 108.8C60.2 109.8 57.9 111 56 112.5C54.1 114.1 52.2 115.8 50.5 118C48.8 120.2 46.9 124 45.9 126C44.9 128 44.9 128.3 44.4 130C44 131.7 43.5 133.5 43.4 136C43.3 138.5 43.4 142.5 43.8 145C44.2 147.5 44.6 148.7 45.6 151C46.6 153.3 48.4 157 49.7 159C50.9 161 51.8 161.8 53 163C54.2 164.2 54.5 164.7 57 166.1C59.5 167.5 65 170.5 68 171.6C71 172.7 72.2 172.6 75 172.7C77.8 172.9 82.5 172.8 85 172.6C87.5 172.4 87.8 172.3 90 171.4C92.2 170.5 95.3 169.1 98 167.1C100.7 165.2 103.9 162.4 106 159.8C108.1 157.3 109.4 154.1 110.4 152C111.5 149.9 111.8 150 112.2 147C112.6 144 112.8 137.2 112.6 134C112.5 130.8 112 130.3 111.1 128C110.2 125.7 108.5 122 107.4 120C106.2 118 105.8 117.4 104.4 116C103 114.6 101.1 112.8 99 111.4C96.9 110 94 108.5 92 107.6C90 106.7 89.7 106.4 87 105.9C84.3 105.5 79.3 104.8 76 105ZM237 104.9C234.7 105.2 231.3 106 229 106.7C226.7 107.5 225 108.3 223 109.5C221 110.7 218.6 112.6 217 114C215.4 115.4 214.4 116.7 213.3 118C212.3 119.3 211.8 120 210.8 122C209.9 124 208.4 127.7 207.6 130C206.9 132.3 206.7 133.8 206.6 136C206.4 138.2 206.5 141.2 206.7 143C206.9 144.8 206.9 145 207.5 147C208.2 149 209.5 152.7 210.7 155C211.8 157.3 213.1 159.3 214.5 161C215.9 162.7 217.4 164.1 219 165.3C220.6 166.6 222 167.4 224 168.5C226 169.5 228.8 170.8 231 171.5C233.2 172.1 234.3 172.4 237 172.6C239.7 172.8 244.2 172.8 247 172.4C249.8 172.1 251.8 171.3 254 170.4C256.2 169.6 258.3 168.3 260 167.2C261.7 166.2 262.8 165.4 264.3 164C265.8 162.6 267.5 161.2 269 159C270.5 156.8 272.3 153 273.2 151C274.1 149 274.2 148.5 274.5 147C274.9 145.5 275.4 144.3 275.5 142C275.6 139.7 275.6 135.7 275.2 133C274.8 130.3 274.2 128.3 273.3 126C272.3 123.7 270.7 120.8 269.5 119C268.4 117.2 267.5 116.2 266.2 115C264.9 113.8 263.9 112.8 262 111.6C260.1 110.4 257 108.6 255 107.6C253 106.7 252 106.3 250 105.8C248 105.4 245.2 105 243 104.8C240.8 104.7 239.3 104.6 237 104.9ZM542 105C540.3 105.2 539 105.3 537 105.9C535 106.5 532 107.6 530 108.7C528 109.7 526.3 110.7 524.8 112C523.3 113.3 522.2 114.6 521 116.3C519.8 118 518.3 120 517.3 122C516.3 124 515.5 126 514.9 128C514.3 130 513.8 131.5 513.6 134C513.3 136.5 513.2 139.8 513.6 143C514 146.2 514.8 150.2 515.9 153C516.9 155.8 518.4 157.8 519.9 160C521.4 162.2 523 164.3 525.2 166C527.4 167.7 530.7 169.4 533 170.4C535.3 171.5 536.3 172 539 172.3C541.7 172.7 546 172.9 549 172.5C552 172.2 554.7 171.2 557 170.3C559.3 169.4 560.8 169 563 167.2C565.2 165.5 568.2 162.4 570.1 160C572 157.6 573.2 155.2 574.2 153C575.2 150.8 575.7 150.2 576.1 147C576.5 143.8 576.7 137.2 576.6 134C576.5 130.8 576 129.8 575.4 128C574.9 126.2 574.2 124.7 573.3 123C572.5 121.3 571.6 119.7 570.3 118C569.1 116.3 567.7 114.6 565.9 113C564.2 111.4 562.2 109.9 560 108.7C557.8 107.5 555.2 106.4 553 105.8C550.8 105.1 548.8 104.9 547 104.8C545.2 104.7 543.7 104.8 542 105ZM690 151.9C686 152.9 680.7 153.9 678 154.9C675.3 155.9 675 156.8 674 157.8C673 158.9 672.5 159.6 672 161C671.5 162.4 671 164.3 671 166C671 167.7 671.3 169.6 671.8 171C672.3 172.4 673 173.3 674 174.4C675 175.5 676.2 176.6 678 177.5C679.8 178.3 682.8 179.1 685 179.5C687.2 179.9 688.7 180 691 180C693.3 180 696.8 179.8 699 179.5C701.2 179.2 702.3 178.8 704 178.2C705.7 177.7 707.5 177 709 176.2C710.5 175.4 711.6 174.8 713 173.6C714.4 172.4 716.1 170.6 717.3 169C718.5 167.4 719.6 165.7 720.3 164C721.1 162.3 721.6 161 721.7 159C721.8 157 721.2 154.2 721 151.7L690 151.9Z';
final class Pdf {
    public float $B; public float $H;
    private array $seiten = []; private ?int $akt = null;
    private static array $W = [];
    private const WIN = [8364 => 128, 8218 => 130, 402 => 131, 8222 => 132, 8230 => 133, 8224 => 134, 8225 => 135, 710 => 136,
        8240 => 137, 352 => 138, 8249 => 139, 338 => 140, 381 => 142, 8216 => 145, 8217 => 146, 8220 => 147, 8221 => 148,
        8226 => 149, 8211 => 150, 8212 => 151, 732 => 152, 8482 => 153, 353 => 154, 8250 => 155, 339 => 156, 382 => 158,
        376 => 159, 8722 => 45, 8201 => 32, 8239 => 32, 160 => 32];

    public function __construct(bool $quer = false) {
        $this->B = $quer ? 841.89 : 595.28; $this->H = $quer ? 595.28 : 841.89;
        if (!self::$W) {
            self::$W['F1'] = self::breiten("278 278 355 556 556 889 667 191 333 333 389 584 278 333 278 278 556*10 278 278 584 584 584 556 1015 " .
              "667 667 722 722 667 611 778 722 278 500 667 556 833 722 778 667 778 722 667 611 722 667 944 667 667 611 278 278 278 469 556 333 " .
              "556 556 500 556 556 278 556 556 222 222 500 222 833 556 556 556 556 333 500 278 556 500 722 500 500 500 334 260 334 584 350 " .
              "556 350 222 556 333 1000 556 556 333 1000 667 333 1000 350 611 350 350 222 222 333 333 350 556 1000 333 1000 500 333 944 350 500 667 " .
              "278 333 556 556 556 556 260 556 333 737 370 556 584 333 737 333 400 584 333 333 333 556 537 278 333 333 365 556 834 834 834 611 " .
              "667*6 1000 722 667*4 278*4 722 722 778*5 584 778 722*4 667 667 611 556*6 889 500 556*4 278*4 556 556 556*5 584 611 556*4 500 556 500");
            self::$W['F2'] = self::breiten("278 333 474 556 556 889 722 238 333 333 389 584 278 333 278 278 556*10 333 333 584 584 584 611 975 " .
              "722 722 722 722 667 611 778 722 278 556 722 611 833 722 778 667 778 722 667 611 722 667 944 667 667 611 333 278 333 584 556 333 " .
              "556 611 556 611 556 333 611 611 278 278 556 278 889 611 611 611 611 389 556 333 611 556 778 556 556 500 389 280 389 584 350 " .
              "556 350 278 556 500 1000 556 556 333 1000 667 333 1000 350 611 350 350 278 278 500 500 350 556 1000 333 1000 556 333 944 350 500 667 " .
              "278 333 556 556 556 556 280 556 333 737 370 556 584 333 737 333 400 584 333 333 333 611 556 278 333 333 365 556 834 834 834 611 " .
              "722*6 1000 722 667*4 278*4 722 722 778*5 584 778 722*4 667 667 611 556*6 889 556 556*4 278*4 611 611 611*5 584 611 611*4 556 611 556");
        }
    }
    private static function breiten(string $s): array {
        $aus = [];
        foreach (explode(' ', $s) as $t) { $m = explode('*', $t); $n = isset($m[1]) ? (int)$m[1] : 1; for ($i = 0; $i < $n; $i++) $aus[] = (int)$m[0]; }
        return $aus;
    }
    private static function codes(?string $s): array {
        $aus = [];
        foreach (preg_split('//u', (string)$s, -1, PREG_SPLIT_NO_EMPTY) as $ch) {
            $c = mb_ord($ch, 'UTF-8');
            if (isset(self::WIN[$c])) $aus[] = self::WIN[$c];
            elseif (($c >= 32 && $c < 127) || ($c >= 160 && $c <= 255)) $aus[] = $c;
            else { $z = @iconv('UTF-8', 'ASCII//TRANSLIT', $ch); $aus[] = ($z !== false && $z !== '' && ord($z[0]) >= 32 && ord($z[0]) < 127 && $z[0] !== '?') ? ord($z[0]) : 63; }
        }
        return $aus;
    }
    private static function zahl(float $v): string { $r = round($v, 2); return $r == (int)$r ? (string)(int)$r : rtrim(rtrim(sprintf('%.2f', $r), '0'), '.'); }
    private static function fein(float $v): string { return rtrim(rtrim(sprintf('%.6f', $v), '0'), '.'); }
    private static function rgb($f): array {
        if (is_string($f)) { $n = hexdec(substr($f, 1)); return [($n >> 16 & 255) / 255, ($n >> 8 & 255) / 255, ($n & 255) / 255]; }
        return $f;
    }
    private static function farbe($f, string $op): string { $f = self::rgb($f); return self::zahl($f[0]) . ' ' . self::zahl($f[1]) . ' ' . self::zahl($f[2]) . ' ' . $op; }
    private static function pdfText(?string $s): string {
        $o = '';
        foreach (self::codes($s) as $c) $o .= ($c === 40 || $c === 41 || $c === 92 ? '\\' : '') . chr($c);
        return '(' . $o . ')';
    }
    private function y(float $v): string { return self::zahl($this->H - $v); }

    public function weite(?string $s, float $gr = 10, bool $fett = false): float {
        $w = self::$W[$fett ? 'F2' : 'F1']; $sum = 0;
        foreach (self::codes($s) as $c) $sum += $w[$c - 32] ?? 556;
        return $sum * $gr / 1000;
    }
    public function kuerzen(?string $s, float $max, float $gr = 10, bool $fett = false): string {
        $s = (string)$s;
        if (!$max || $this->weite($s, $gr, $fett) <= $max) return $s;
        $z = preg_split('//u', $s, -1, PREG_SPLIT_NO_EMPTY);
        while ($z && $this->weite(implode('', $z) . '…', $gr, $fett) > $max) array_pop($z);
        return preg_replace('/[\s,.;:·–-]+$/u', '', implode('', $z)) . '…';
    }
    public function umbrechen(string $s, float $max, float $gr = 10, bool $fett = false): array {
        $zeilen = []; $zeile = '';
        foreach (preg_split('/\s+/u', $s) as $wort) {
            $neu = $zeile !== '' ? $zeile . ' ' . $wort : $wort;
            if ($zeile !== '' && $this->weite($neu, $gr, $fett) > $max) { $zeilen[] = $zeile; $zeile = $wort; } else $zeile = $neu;
        }
        if ($zeile !== '') $zeilen[] = $zeile;
        return $zeilen;
    }

    public function seite(): int { $this->seiten[] = ['inhalt' => [], 'links' => []]; $this->akt = count($this->seiten) - 1; return $this->akt; }
    public function auf(int $n): void { $this->akt = $n; }
    public function anzahl(): int { return count($this->seiten); }
    private function zu(string $s): void { $this->seiten[$this->akt]['inhalt'][] = $s; }

    /** o: gr, fett, farbe, rechts (x = rechter Rand), mitte (x = Mitte), max */
    public function text(float $x, float $y, ?string $s, array $o = []): float {
        $gr = $o['gr'] ?? 10; $fett = !empty($o['fett']);
        $t = !empty($o['max']) ? $this->kuerzen($s, $o['max'], $gr, $fett) : (string)$s; $w = $this->weite($t, $gr, $fett);
        if (!empty($o['rechts'])) $x -= $w; elseif (!empty($o['mitte'])) $x -= $w / 2;
        $this->zu('BT /' . ($fett ? 'F2' : 'F1') . ' ' . self::zahl($gr) . ' Tf ' . self::farbe($o['farbe'] ?? [0.102, 0.102, 0.098], 'rg') .
            ' ' . self::zahl($x) . ' ' . $this->y($y) . ' Td ' . self::pdfText($t) . ' Tj ET');
        return $w;
    }
    private function rundPfad(float $x, float $yy, float $b, float $h, float $r): string {
        $r = min($r, $b / 2, $h / 2); $k = $r * 0.5523; $x2 = $x + $b; $y2 = $yy + $h; $z = fn($v) => self::zahl($v); $y = fn($v) => $this->y($v);
        return implode(' ', [$z($x + $r) . ' ' . $y($yy) . ' m', $z($x2 - $r) . ' ' . $y($yy) . ' l',
            $z($x2 - $r + $k) . ' ' . $y($yy) . ' ' . $z($x2) . ' ' . $y($yy + $r - $k) . ' ' . $z($x2) . ' ' . $y($yy + $r) . ' c',
            $z($x2) . ' ' . $y($y2 - $r) . ' l',
            $z($x2) . ' ' . $y($y2 - $r + $k) . ' ' . $z($x2 - $r + $k) . ' ' . $y($y2) . ' ' . $z($x2 - $r) . ' ' . $y($y2) . ' c',
            $z($x + $r) . ' ' . $y($y2) . ' l',
            $z($x + $r - $k) . ' ' . $y($y2) . ' ' . $z($x) . ' ' . $y($y2 - $r + $k) . ' ' . $z($x) . ' ' . $y($y2 - $r) . ' c',
            $z($x) . ' ' . $y($yy + $r) . ' l',
            $z($x) . ' ' . $y($yy + $r - $k) . ' ' . $z($x + $r - $k) . ' ' . $y($yy) . ' ' . $z($x + $r) . ' ' . $y($yy) . ' c h']);
    }
    public function rechteck(float $x, float $y, float $b, float $h, $f, float $radius = 0, $rand = null, float $staerke = 0.75): void {
        $pfad = $radius ? $this->rundPfad($x, $y, $b, $h, $radius) : self::zahl($x) . ' ' . $this->y($y + $h) . ' ' . self::zahl($b) . ' ' . self::zahl($h) . ' re';
        if ($f && $rand) $this->zu(self::farbe($f, 'rg') . ' ' . self::farbe($rand, 'RG') . ' ' . self::zahl($staerke) . ' w ' . $pfad . ' B');
        elseif ($f) $this->zu(self::farbe($f, 'rg') . ' ' . $pfad . ' f');
        elseif ($rand) $this->zu(self::farbe($rand, 'RG') . ' ' . self::zahl($staerke) . ' w ' . $pfad . ' S');
    }
    public function kreis(float $x, float $y, float $r, $f): void { $this->rechteck($x - $r, $y - $r, 2 * $r, 2 * $r, $f, $r); }
    public function linie(float $x1, float $y1, float $x2, float $y2, $f = [0.8, 0.8, 0.78], float $st = 0.5): void {
        $this->zu('0 J ' . self::farbe($f, 'RG') . ' ' . self::zahl($st) . ' w ' . self::zahl($x1) . ' ' . $this->y($y1) . ' m ' . self::zahl($x2) . ' ' . $this->y($y2) . ' l S');
    }
    /** Linienzug durch Punkte [[x, y], …] */
    public function zug(array $pkt, $f, float $st = 1): void {
        $s = '1 J 1 j ' . self::farbe($f, 'RG') . ' ' . self::zahl($st) . ' w';
        foreach ($pkt as $i => [$x, $y]) $s .= ' ' . self::zahl($x) . ' ' . $this->y($y) . ($i ? ' l' : ' m');
        $this->zu($s . ' S');
    }
    private static function svgPfad(string $d): string {
        preg_match_all('/[MLHVQCZ]|-?\d*\.?\d+(?:e-?\d+)?/i', $d, $m); $t = $m[0]; $i = 0; $out = []; $cx = $cy = $sx = $sy = 0; $cmd = '';
        $n = function () use (&$t, &$i) { return (float)$t[$i++]; }; $z = fn($v) => self::zahl($v);
        while ($i < count($t)) {
            if (ctype_alpha($t[$i])) $cmd = $t[$i++];
            switch ($cmd) {
                case 'M': $cx = $sx = $n(); $cy = $sy = $n(); $out[] = $z($cx) . ' ' . $z($cy) . ' m'; $cmd = 'L'; break;
                case 'L': $cx = $n(); $cy = $n(); $out[] = $z($cx) . ' ' . $z($cy) . ' l'; break;
                case 'H': $cx = $n(); $out[] = $z($cx) . ' ' . $z($cy) . ' l'; break;
                case 'V': $cy = $n(); $out[] = $z($cx) . ' ' . $z($cy) . ' l'; break;
                case 'C': $a = [$n(), $n(), $n(), $n(), $n(), $n()]; $out[] = implode(' ', array_map($z, $a)) . ' c'; $cx = $a[4]; $cy = $a[5]; break;
                case 'Q': $qx = $n(); $qy = $n(); $ex = $n(); $ey = $n();
                    $out[] = implode(' ', array_map($z, [$cx + 2 / 3 * ($qx - $cx), $cy + 2 / 3 * ($qy - $cy), $ex + 2 / 3 * ($qx - $ex), $ey + 2 / 3 * ($qy - $ey), $ex, $ey])) . ' c';
                    $cx = $ex; $cy = $ey; break;
                case 'Z': case 'z': $out[] = 'h'; $cx = $sx; $cy = $sy; if ($i < count($t) && !ctype_alpha($t[$i])) $i++; break;
                default: $i++;
            }
        }
        return implode(' ', $out);
    }
    public function svg(string $d, float $x, float $y, float $m, $f, array $o = []): void {
        $mat = 'q ' . self::fein($m) . ' 0 0 ' . self::fein(-$m) . ' ' . self::zahl($x) . ' ' . $this->y($y) . ' cm ';
        $this->zu($mat . (!empty($o['strich']) ? '1 J 1 j ' . self::farbe($f, 'RG') . ' ' . self::zahl($o['strich']) . ' w ' . self::svgPfad($d) . ' S'
            : self::farbe($f, 'rg') . ' ' . self::svgPfad($d) . ' f') . ' Q');
    }
    public function link(float $x, float $y, float $b, float $h, string $url): void { $this->seiten[$this->akt]['links'][] = [$x, $y, $b, $h, $url]; }

    /** fertiges PDF als Bytes */
    public function bytes(string $titel = 'Bondarium'): string {
        $obj = []; $kids = []; $n = 6;
        $obj[3] = '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>';
        $obj[4] = '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>';
        $obj[5] = '<< /Title ' . self::pdfText($titel) . ' /Producer (Bondarium) /CreationDate (D:' . date('YmdHis') . ') >>';
        foreach ($this->seiten as $s) {
            $seite = $n++; $inhalt = $n++; $annots = [];
            foreach ($s['links'] as $l) {
                $annots[] = $n;
                $obj[$n++] = '<< /Type /Annot /Subtype /Link /Rect [' . self::zahl($l[0]) . ' ' . $this->y($l[1] + $l[3]) . ' ' . self::zahl($l[0] + $l[2]) . ' ' .
                    $this->y($l[1]) . '] /Border [0 0 0] /A << /S /URI /URI ' . self::pdfText($l[4]) . ' >> >>';
            }
            $strom = implode("\n", $s['inhalt']);
            $obj[$inhalt] = '<< /Length ' . strlen($strom) . " >>\nstream\n" . $strom . "\nendstream";
            $obj[$seite] = '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ' . self::zahl($this->B) . ' ' . self::zahl($this->H) .
                '] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents ' . $inhalt . ' 0 R' .
                ($annots ? ' /Annots [' . implode(' ', array_map(fn($a) => $a . ' 0 R', $annots)) . ']' : '') . ' >>';
            $kids[] = $seite . ' 0 R';
        }
        $obj[1] = '<< /Type /Catalog /Pages 2 0 R >>';
        $obj[2] = '<< /Type /Pages /Kids [' . implode(' ', $kids) . '] /Count ' . count($kids) . ' >>';
        $out = "%PDF-1.4\n%\xE2\xE3\xCF\xD3\n"; $lagen = [];
        for ($i = 1; $i < $n; $i++) { $lagen[$i] = strlen($out); $out .= $i . " 0 obj\n" . $obj[$i] . "\nendobj\n"; }
        $xref = strlen($out);
        $out .= "xref\n0 " . $n . "\n0000000000 65535 f \n";
        for ($i = 1; $i < $n; $i++) $out .= sprintf('%010d', $lagen[$i]) . " 00000 n \n";
        return $out . "trailer\n<< /Size " . $n . " /Root 1 0 R /Info 5 0 R >>\nstartxref\n" . $xref . "\n%%EOF\n";
    }
}


const B_INK = [0.102, 0.102, 0.098], B_GRAU = [0.333, 0.329, 0.31], B_GRUEN = [0.224, 1, 0.078], B_LINIE = [0.86, 0.86, 0.84];
const B_DUNKEL = '#157C00', B_ROT = '#B3261E', B_FLAECHE = '#F3F2EC', B_BALKEN = '#CFCEC6';

function b_zahl(float $n, int $st = 0): string { return number_format($n, $st, ',', '.'); }
function b_tag(string $iso): string { return substr($iso, 8, 2) . '.' . substr($iso, 5, 2) . '.'; }
/** Veränderung in Prozent: [Text, Farbe]; ohne Vergleichswert „–“ */
function b_delta(?float $jetzt, ?float $vorher): array {
    if ($vorher === null || $jetzt === null) return ['–', B_GRAU];
    if ($vorher == 0) return [$jetzt > 0 ? 'neu' : '–', B_GRAU];
    $p = round(($jetzt - $vorher) / $vorher * 100);
    if ($p == 0) return ['±0 %', B_GRAU];
    return [($p > 0 ? '+' : '–') . b_zahl(abs($p)) . ' %', $p > 0 ? B_DUNKEL : B_ROT];
}
/** Summe der Tageswerte von $bis zurück über $n Tage; null, wenn kein einziger Tag gezählt wurde */
function b_summe(array $verlauf, string $bis, int $n, string $feld): ?float {
    $s = 0; $da = false;
    for ($i = 0; $i < $n; $i++) {
        $t = date('Y-m-d', strtotime("$bis -$i day"));
        if (isset($verlauf[$t])) { $s += $verlauf[$t][$feld]; $da = true; }
    }
    return $da ? $s : null;
}

// Logo 06 (Reinzeichnung, seit 04.10.2026) wie in der Kopfzeile der Website: Bildzeichen nur aus Flächen, Wortmarke im Pixelmaß der Vorlage
const BERICHT_LOGO_B = 'M20.9 19.75C20.9 15.19 24.59 11.5 29.15 11.5C33.71 11.5 37.4 15.19 37.4 19.75L37.4 41C41.5 36.2 47 33.6 53.5 33.6C68 33.6 79.8 46.5 79.8 61C79.8 77.9 66.3 91.7 49.6 91.7C34.5 91.7 20.9 79.5 20.9 64Z';
const BERICHT_LOGO_INNEN = 'M62 63C62 69.9 56.4 75.5 49.5 75.5C42.6 75.5 37 69.9 37 63C37 56.1 42.6 50.5 49.5 50.5C56.4 50.5 62 56.1 62 63ZM81.5 48.5C81.5 56.29 75.19 62.6 67.4 62.6C59.61 62.6 53.3 56.29 53.3 48.5C53.3 40.71 59.61 34.4 67.4 34.4C75.19 34.4 81.5 40.71 81.5 48.5Z';
function bericht_logo(Pdf $P, float $x, float $yo, string $wortPfad): void {
    $m = 28 / 100;
    $P->rechteck($x, $yo, 28, 28, B_INK, 22 * $m);
    $P->svg(BERICHT_LOGO_B, $x, $yo, $m, '#FBFAF7');
    $P->svg(BERICHT_LOGO_INNEN, $x, $yo, $m, B_INK);
    $P->kreis($x + 67.4 * $m, $yo + 48.5 * $m, 11.2 * $m, B_GRUEN);
    $s = 28 / 387; $wx = $x + 28 + 57 * $s; $wy = $yo + 78 * 28 / 381;
    $P->svg($wortPfad, $wx, $wy, $s, B_INK);
    $P->kreis($wx + 899.3 * $s, $wy + 28.6 * $s, 27 * $s, B_DUNKEL);
}

/**
 * $d: tag (Y-m-d, der berichtete Tag), erstellt (Y-m-d H:i), beginn (Y-m-d, erster Zähltag),
 *     verlauf [Y-m-d => [b => Besucher, a => Aufrufe]], monat/jahr [b, a] (bis einschließlich tag),
 *     seiten [[pfad, titel, aufrufe]], herkunft [Gruppe => [Name => Besucher] | Besucher], geraete [Name => Besucher],
 *     bots (ausgefilterte Abrufe), vorschau (bool)
 */
function bericht_pdf(array $d, string $wortPfad = BERICHT_WORTMARKE): string {
    $P = new Pdf(); $B = $P->B; $H = $P->H; $R = 40; $W = $B - 2 * $R;
    $WT = ['Sonntag', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag'];
    $MO = ['', 'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'];
    $tag = $d['tag']; $ts = strtotime($tag); $v = $d['verlauf'];
    $heute = $v[$tag] ?? ['b' => 0, 'a' => 0];
    $vortag = $v[date('Y-m-d', strtotime("$tag -1 day"))] ?? null;
    $vorwoche = $v[date('Y-m-d', strtotime("$tag -7 day"))] ?? null;
    $LINK = 'https://www.bondarium.de/';
    $wann = $tag === date('Y-m-d') ? 'heute' : 'gestern';   // Testmail über den laufenden Tag

    $P->seite();
    $P->rechteck(0, 0, $B, 56, B_GRUEN);
    bericht_logo($P, $R, 14, $wortPfad);
    $P->text($B - $R, 35, 'www.bondarium.de', ['gr' => 9, 'rechts' => true]);
    $P->link($B - $R - $P->weite('www.bondarium.de', 9), 24, $P->weite('www.bondarium.de', 9), 14, $LINK);

    $P->text($R, 94, 'Besucherbericht', ['gr' => 24, 'fett' => true]);
    $erst = strtotime($d['erstellt']);
    $P->text($R, 114, $WT[date('w', $ts)] . ', ' . date('j', $ts) . '. ' . $MO[date('n', $ts)] . ' ' . date('Y', $ts) .
        ' · erstellt am ' . date('d.m.Y', $erst) . ' um ' . date('H:i', $erst) . ' Uhr', ['gr' => 9.5, 'farbe' => B_GRAU]);
    if (!empty($d['vorschau'])) {
        $t = 'VORSCHAU MIT BEISPIELDATEN'; $w = $P->weite($t, 7, true) + 16;
        $P->rechteck($B - $R - $w, 80, $w, 17, '#FFF4CC', 8.5, '#E0B000', 0.6);
        $P->text($B - $R - $w / 2, 91.5, $t, ['gr' => 7, 'fett' => true, 'mitte' => true, 'farbe' => '#6B5200']);
    }

    // ---- Kennzahlen: vier Kacheln ----
    $kw = ($W - 30) / 4; $ky = 134; $kh = 76;
    // Durchschnitt nur über Tage seit Beginn der Zählung – sonst zöge die erste Woche den Wert nach unten
    $schnitt = function ($bis) use ($v, $d) {
        $s = b_summe($v, $bis, 7, 'b'); if ($s === null) return null;
        $n = 0; for ($i = 0; $i < 7; $i++) if (date('Y-m-d', strtotime("$bis -$i day")) >= $d['beginn']) $n++;
        return $s / max(1, $n);
    };
    $s7 = $schnitt($tag); $s7v = $schnitt(date('Y-m-d', strtotime("$tag -7 day")));
    $wtk = ['So.', 'Mo.', 'Di.', 'Mi.', 'Do.', 'Fr.', 'Sa.'][date('w', $ts)];
    $kacheln = [
        ['Besucher', b_zahl($heute['b']), b_delta($heute['b'], $vortag['b'] ?? null), 'zum Vortag', b_delta($heute['b'], $vorwoche['b'] ?? null), "zum $wtk der Vorwoche"],
        ['Seitenaufrufe', b_zahl($heute['a']), b_delta($heute['a'], $vortag['a'] ?? null), 'zum Vortag', b_delta($heute['a'], $vorwoche['a'] ?? null), "zum $wtk der Vorwoche"],
        ['Seiten je Besucher', $heute['b'] ? b_zahl($heute['a'] / $heute['b'], 1) : '–',
            b_delta($heute['b'] ? $heute['a'] / $heute['b'] : null, $vortag && $vortag['b'] ? $vortag['a'] / $vortag['b'] : null), 'zum Vortag', null, ''],
        ['Ø Besucher 7 Tage', $s7 === null ? '–' : b_zahl($s7), b_delta($s7, $s7v), 'zur Vorwoche', null, $s7v === null ? '' : 'Vorwoche: ' . b_zahl($s7v)],
    ];
    foreach ($kacheln as $i => [$titel, $wert, $d1, $t1, $d2, $t2]) {
        $x = $R + $i * ($kw + 10);
        $P->rechteck($x, $ky, $kw, $kh, B_FLAECHE, 6);
        $P->text($x + 12, $ky + 17, mb_strtoupper($titel), ['gr' => 6.5, 'fett' => true, 'farbe' => B_GRAU]);
        $P->text($x + 12, $ky + 44, $wert, ['gr' => 22, 'fett' => true]);
        $w = $P->text($x + 12, $ky + 58, $d1[0], ['gr' => 7.5, 'fett' => true, 'farbe' => $d1[1]]);
        $P->text($x + 12 + $w + 3, $ky + 58, $t1, ['gr' => 7.5, 'farbe' => B_GRAU]);
        if ($d2) { $w = $P->text($x + 12, $ky + 68, $d2[0], ['gr' => 7.5, 'fett' => true, 'farbe' => $d2[1]]); $P->text($x + 12 + $w + 3, $ky + 68, $t2, ['gr' => 7.5, 'farbe' => B_GRAU]); }
        elseif ($t2) $P->text($x + 12, $ky + 68, $t2, ['gr' => 7.5, 'farbe' => B_GRAU]);
    }

    // ---- Wochenbrief (seit 02.10.2026): Abonnenten neben den Besucherzahlen – ein Band unter den Kacheln; alles darunter rückt nach.
    //      Fehlt die Angabe (Konto-Datenbank nicht lesbar oder noch ohne Newsletter), entfällt das Band. ----
    $nl = $d['newsletter'] ?? null; $versatz = 0;
    if (is_array($nl)) {
        $by = $ky + $kh + 10; $versatz = 34;
        $P->rechteck($R, $by, $W, 24, B_FLAECHE, 6);
        $bx = $R + 12; $bx += $P->text($bx, $by + 15.5, 'WOCHENBRIEF', ['gr' => 6.5, 'fett' => true, 'farbe' => B_GRAU]) + 12;
        $bx += $P->text($bx, $by + 15.8, b_zahl($nl['abonnenten']) . ($nl['abonnenten'] === 1 ? ' Abonnent' : ' Abonnenten'), ['gr' => 10, 'fett' => true]) + 8;
        $teile = [];
        if ($nl['an'] || $nl['ab']) $teile[] = $wann . ' ' . ($nl['an'] ? '+' . b_zahl($nl['an']) : '') . ($nl['an'] && $nl['ab'] ? ' / ' : '') . ($nl['ab'] ? '−' . b_zahl($nl['ab']) : '');
        else $teile[] = $wann . ' unverändert';
        $teile[] = b_zahl($nl['konten']) . ($nl['konten'] === 1 ? ' Konto' : ' Konten');
        if ($nl['letzte']) $teile[] = 'letzte Ausgabe KW ' . (int)substr((string)$nl['letzte']['kw'], -2) . ' an ' . b_zahl((int)$nl['letzte']['empfaenger']) . ' Empfänger';
        else $teile[] = 'noch keine Ausgabe verschickt';
        $P->text($bx, $by + 15.5, implode('  ·  ', $teile), ['gr' => 8, 'farbe' => B_GRAU]);
    }

    // ---- Verlauf: Besucher der letzten 30 Tage (Balken) und 7-Tage-Durchschnitt (Linie) ----
    $y = 240 + $versatz;
    $P->text($R, $y, 'Besucher der letzten 30 Tage', ['gr' => 11, 'fett' => true]);
    $lx = $B - $R; $lx -= $P->text($lx, $y, 'Durchschnitt der letzten 7 Tage', ['gr' => 7, 'farbe' => B_GRAU, 'rechts' => true]) + 4;
    $P->linie($lx - 14, $y - 2.5, $lx, $y - 2.5, B_DUNKEL, 1.4); $lx -= 26;
    $lx -= $P->text($lx, $y, 'Besucher je Tag', ['gr' => 7, 'farbe' => B_GRAU, 'rechts' => true]) + 4;
    $P->rechteck($lx - 7, $y - 6.5, 7, 7, B_BALKEN, 1);
    $tage = []; for ($i = 29; $i >= 0; $i--) $tage[] = date('Y-m-d', strtotime("$tag -$i day"));
    $max = max([1, ...array_map(fn($t) => $v[$t]['b'] ?? 0, $tage)]);
    $schritt = 1; foreach ([1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 2500, 5000, 10000, 20000, 50000] as $s) { $schritt = $s; if ($max / $s <= 4) break; }
    $oben = ceil($max * 1.08 / $schritt) * $schritt;
    $cx = $R + 30; $cw = $B - $R - $cx; $c0 = $y + 18; $ch = 104 - $versatz; $cu = $c0 + $ch;   // mit dem Wochenbrief-Band ist das Schaubild um dessen Höhe niedriger – alles darunter bleibt, wo es war
    for ($g = 0; $g <= $oben; $g += $schritt) {
        $gy = $cu - $g / $oben * $ch;
        $P->linie($cx, $gy, $B - $R, $gy, $g ? B_LINIE : B_GRAU, $g ? 0.4 : 0.6);
        $P->text($cx - 6, $gy + 2.5, b_zahl($g), ['gr' => 6.5, 'farbe' => B_GRAU, 'rechts' => true]);
    }
    $bw = $cw / 30; $linie = [];
    foreach ($tage as $i => $t) {
        $bx = $cx + $i * $bw; $wert = $v[$t]['b'] ?? null; $letzter = $i === 29;
        if ($wert) {
            $h = $wert / $oben * $ch;
            $P->rechteck($bx + $bw * 0.16, $cu - $h, $bw * 0.68, $h, $letzter ? B_INK : B_BALKEN);
            if ($letzter) $P->text($bx + $bw / 2, $cu - $h - 4, b_zahl($wert), ['gr' => 7, 'fett' => true, 'mitte' => true]);
        }
        if (($m = b_summe($v, $t, 7, 'b')) !== null && isset($v[date('Y-m-d', strtotime("$t -6 day"))])) $linie[] = [$bx + $bw / 2, $cu - $m / 7 / $oben * $ch];
        if ((29 - $i) % 7 === 0) $P->text($bx + $bw / 2, $cu + 11, b_tag($t), ['gr' => 6.5, 'farbe' => $letzter ? B_INK : B_GRAU, 'fett' => $letzter, 'mitte' => true]);
    }
    if (count($linie) > 1) $P->zug($linie, B_DUNKEL, 1.4);

    // ---- Zeiträume ----
    $y = $cu + 40;
    $P->text($R, $y, 'Zeiträume', ['gr' => 11, 'fett' => true]);
    $vm = date('Y-m-d', strtotime("$tag -1 day"));
    $spalten = [
        [ucfirst($wann), $heute['b'], $heute['a'], b_delta($heute['b'], $vortag['b'] ?? null), 'zum Vortag'],
        ['Letzte 7 Tage', b_summe($v, $tag, 7, 'b'), b_summe($v, $tag, 7, 'a'), b_delta(b_summe($v, $tag, 7, 'b'), b_summe($v, date('Y-m-d', strtotime("$tag -7 day")), 7, 'b')), 'zu den 7 Tagen davor'],
        ['Letzte 30 Tage', b_summe($v, $tag, 30, 'b'), b_summe($v, $tag, 30, 'a'), b_delta(b_summe($v, $tag, 30, 'b'), b_summe($v, date('Y-m-d', strtotime("$tag -30 day")), 30, 'b')), 'zu den 30 Tagen davor'],
        [$MO[date('n', $ts)] . (date('j', strtotime("$tag +1 day")) == 1 ? '' : ' bisher'), $d['monat'][0], $d['monat'][1], null, ''],
        [date('Y', $ts) . ' bisher', $d['jahr'][0], $d['jahr'][1], null, 'seit ' . date('d.m.Y', strtotime($d['beginn']))],
    ];
    $tx = $R + 92; $sw = ($B - $R - $tx) / count($spalten); $y += 18;
    $P->text($R, $y + 15, 'Besucher', ['gr' => 8.5, 'farbe' => B_GRAU]);
    $P->text($R, $y + 31, 'Seitenaufrufe', ['gr' => 8.5, 'farbe' => B_GRAU]);
    $P->text($R, $y + 46, 'Veränderung', ['gr' => 7.5, 'farbe' => B_GRAU]);
    foreach ($spalten as $i => [$titel, $b, $a, $dl, $hint]) {
        $rx = $tx + ($i + 1) * $sw - 4;
        $P->text($rx, $y, mb_strtoupper($titel), ['gr' => 6.5, 'fett' => true, 'farbe' => B_GRAU, 'rechts' => true]);
        $P->text($rx, $y + 15, $b === null ? '–' : b_zahl($b), ['gr' => 10, 'fett' => true, 'rechts' => true]);
        $P->text($rx, $y + 31, $a === null ? '–' : b_zahl($a), ['gr' => 9, 'rechts' => true]);
        if ($dl) $P->text($rx, $y + 46, $dl[0], ['gr' => 7.5, 'fett' => true, 'farbe' => $dl[1], 'rechts' => true]);
        $P->text($rx, $y + 56, $hint, ['gr' => 6, 'farbe' => B_GRAU, 'rechts' => true]);
    }
    $P->linie($R, $y + 5, $B - $R, $y + 5, B_INK, 0.8);
    $P->linie($R, $y + 20, $B - $R, $y + 20, B_LINIE, 0.4);
    $P->linie($R, $y + 36, $B - $R, $y + 36, B_LINIE, 0.4);

    // ---- unten links: meistbesuchte Seiten ----
    $y += 92; $lw = 255; $rx0 = $R + $lw + 25; $rw = $B - $R - $rx0;
    $P->text($R, $y, 'Meistbesuchte Seiten ' . $wann, ['gr' => 11, 'fett' => true]);
    $P->text($R, $y + 16, 'SEITE', ['gr' => 6.5, 'fett' => true, 'farbe' => B_GRAU]);
    $P->text($R + $lw, $y + 16, 'AUFRUFE', ['gr' => 6.5, 'fett' => true, 'farbe' => B_GRAU, 'rechts' => true]);
    $P->linie($R, $y + 21, $R + $lw, $y + 21, B_INK, 0.8);
    $smax = max([1, ...array_map(fn($s) => $s[2], $d['seiten'])]); $sy = $y + 21;
    foreach (array_slice($d['seiten'], 0, 10) as $s) {
        [$pfad, $titel, $n] = $s;
        $P->text($R, $sy + 13, $titel, ['gr' => 8.5, 'max' => 172]);
        $P->link($R, $sy + 3, min(172, $P->weite($titel, 8.5)), 13, $LINK . ltrim($pfad, '/'));
        $P->rechteck($R + 180, $sy + 6.5, max(1.5, 42 * $n / $smax), 8, B_BALKEN, 1);
        $P->text($R + $lw, $sy + 13, b_zahl($n), ['gr' => 8.5, 'rechts' => true]);
        $sy += 18; $P->linie($R, $sy, $R + $lw, $sy, B_LINIE, 0.4);
    }
    $rest = ($d['seiten_anzahl'] ?? count($d['seiten'])) - min(10, count($d['seiten']));
    if ($rest > 0) $P->text($R, $sy + 12, 'und ' . b_zahl($rest) . ' weitere Seiten mit zusammen ' . b_zahl($heute['a'] - array_sum(array_map(fn($s) => $s[2], array_slice($d['seiten'], 0, 10)))) . ' Aufrufen', ['gr' => 7, 'farbe' => B_GRAU]);

    // ---- unten rechts: Herkunft und Geräte ----
    $P->text($rx0, $y, 'Woher die Besucher kamen', ['gr' => 11, 'fett' => true]);
    $P->text($rx0, $y + 16, 'HERKUNFT', ['gr' => 6.5, 'fett' => true, 'farbe' => B_GRAU]);
    $P->text($B - $R, $y + 16, 'BESUCHER', ['gr' => 6.5, 'fett' => true, 'farbe' => B_GRAU, 'rechts' => true]);
    $P->linie($rx0, $y + 21, $B - $R, $y + 21, B_INK, 0.8);
    $gesamt = 0; foreach ($d['herkunft'] as $g) $gesamt += is_array($g) ? array_sum($g) : $g;
    $hy = $y + 21;
    foreach ($d['herkunft'] as $gruppe => $g) {
        $n = is_array($g) ? array_sum($g) : $g;
        $P->text($rx0, $hy + 13, $gruppe, ['gr' => 8.5, 'fett' => true]);
        $P->text($B - $R - 34, $hy + 13, b_zahl($n), ['gr' => 8.5, 'fett' => true, 'rechts' => true]);
        $P->text($B - $R, $hy + 13, $gesamt ? b_zahl($n / $gesamt * 100) . ' %' : '–', ['gr' => 8, 'farbe' => B_GRAU, 'rechts' => true]);
        $hy += 16;
        if (is_array($g)) {
            arsort($g); $teile = []; $k = 0; $sonst = 0;
            foreach ($g as $name => $z) { if ($k++ < 4) $teile[] = $name . ' ' . b_zahl($z); else $sonst += $z; }
            if ($sonst) $teile[] = 'weitere ' . b_zahl($sonst);
            foreach ($P->umbrechen(implode(' · ', $teile), $rw - 10, 7.5) as $zeile) { $P->text($rx0 + 10, $hy + 6, $zeile, ['gr' => 7.5, 'farbe' => B_GRAU]); $hy += 10; }
            $hy += 4;
        }
        $P->linie($rx0, $hy, $B - $R, $hy, B_LINIE, 0.4);
    }

    $gy = $hy + 26;
    $P->text($rx0, $gy, 'Geräte', ['gr' => 11, 'fett' => true]);
    $gsum = array_sum($d['geraete']); $gx = $rx0; $farben = [B_INK, '#8C8B84', B_BALKEN]; $i = 0;
    foreach ($d['geraete'] as $n) { $w = $gsum ? $rw * $n / $gsum : 0; $P->rechteck($gx, $gy + 9, $w, 10, $farben[$i++ % 3]); $gx += $w; }
    $gx = $rx0; $i = 0;
    foreach ($d['geraete'] as $name => $n) {
        $P->rechteck($gx, $gy + 28, 7, 7, $farben[$i++ % 3], 1);
        $gx += 10 + $P->text($gx + 10, $gy + 34.5, $name . ' ' . ($gsum ? b_zahl($n / $gsum * 100) : '0') . ' %', ['gr' => 7.5]) + 14;
    }

    // ---- Fuß: so wird gezählt ----
    $noten = [
        'So wird gezählt: ohne Cookies und ohne Speicherung im Browser. „Besucher“ heißt: verschiedene Besucher an einem Tag. Dafür bildet der Server aus IP-Adresse und Browser-Kennung ' .
        'eine Prüfsumme, die jeden Tag neu verschlüsselt wird; die IP-Adresse selbst wird nicht gespeichert. Über mehrere Tage sind die Besucher deshalb die Summe der Tageswerte – wer an zwei Tagen kommt, zählt zweimal.',
        'Robots und automatisierte Browser werden aussortiert (' . $wann . ' ' . b_zahl($d['bots']) . ' Abrufe); Robots, die kein JavaScript ausführen – die meisten Suchmaschinen –, kommen gar nicht erst an. ' .
        'Nicht gezählt werden auch Besucher mit abgeschaltetem JavaScript oder mit „Global Privacy Control“ bzw. „Do Not Track“ im Browser. ' .
        'Herkunft: die Website, von der ein Besucher an diesem Tag zuerst kam; Suchbegriffe übermitteln die Suchmaschinen nicht.',
    ];
    $fuss = []; foreach ($noten as $t) $fuss = array_merge($fuss, $P->umbrechen($t, $W, 7));
    $fy = $H - 34 - count($fuss) * 9;
    $P->linie($R, $fy - 12, $B - $R, $fy - 12, B_LINIE, 0.5);
    foreach ($fuss as $z) { $P->text($R, $fy, $z, ['gr' => 7, 'farbe' => B_GRAU]); $fy += 9; }
    $P->text($R, $H - 22, 'Bondarium – Besucherbericht · automatisch erstellt, nur für den internen Gebrauch', ['gr' => 7, 'farbe' => B_GRAU]);
    $P->text($B - $R, $H - 22, 'Seite 1 von 1', ['gr' => 7, 'farbe' => B_GRAU, 'rechts' => true]);
    return $P->bytes('Besucherbericht ' . date('d.m.Y', $ts) . ' – Bondarium');
}

// ---------- Zahlen aus der Datenbank ----------

/** Kurzer Seitenname aus dem <title> der Datei („Zinskurve seit 1972: Deutschland und USA – Bondarium“ → „Zinskurve seit 1972“) */
function bericht_seitenname(string $pfad): string
{
    if ($pfad === '/') return 'Startseite';
    if ($pfad === '/anleihe.html') return 'Anleihe-Steckbriefe (alle)';
    $html = @file_get_contents(__DIR__ . $pfad, false, null, 0, 20000);
    if ($html && preg_match('~<title>(.*?)</title>~si', $html, $m)) {
        $t = trim(html_entity_decode($m[1], ENT_QUOTES | ENT_HTML5, 'UTF-8'));
        $t = trim(preg_replace('~\s*[–-]\s*Bondarium$~u', '', $t));
        $t = trim(explode(':', $t)[0]);
        if ($t !== '') return $t;
    }
    return ltrim($pfad, '/');
}

function bericht_daten(PDO $db, string $tag): array
{
    $ts = strtotime($tag);
    $s = $db->prepare('SELECT tag, besucher, aufrufe FROM tage WHERE tag BETWEEN ? AND ? AND (besucher > 0 OR aufrufe > 0)');
    $s->execute([date('Y-m-d', strtotime("$tag -70 day")), $tag]);
    $verlauf = [];
    foreach ($s->fetchAll(PDO::FETCH_NUM) as [$t, $b, $a]) $verlauf[$t] = ['b' => (int)$b, 'a' => (int)$a];
    $summe = function (string $von) use ($db, $tag): array {
        $s = $db->prepare('SELECT COALESCE(SUM(besucher), 0), COALESCE(SUM(aufrufe), 0) FROM tage WHERE tag BETWEEN ? AND ?');
        $s->execute([$von, $tag]);
        return array_map('intval', $s->fetch(PDO::FETCH_NUM));
    };
    $beginn = (string)($db->query('SELECT MIN(tag) FROM tage WHERE besucher > 0')->fetchColumn() ?: $tag);

    $s = $db->prepare('SELECT pfad, aufrufe FROM seiten WHERE tag = ? ORDER BY aufrufe DESC, pfad');
    $s->execute([$tag]);
    $alle = $s->fetchAll(PDO::FETCH_NUM);
    $seiten = array_map(fn($z) => [$z[0], bericht_seitenname($z[0]), (int)$z[1]], array_slice($alle, 0, 10));

    $herkunft = ['Suchmaschinen' => [], 'KI-Assistenten' => [], 'Andere Websites' => [], 'Direkt oder unbekannt' => 0];
    $s = $db->prepare('SELECT gruppe, quelle, besucher FROM herkunft WHERE tag = ?');
    $s->execute([$tag]);
    foreach ($s->fetchAll(PDO::FETCH_NUM) as [$g, $q, $n]) {
        if (!array_key_exists($g, $herkunft)) continue;
        if (is_array($herkunft[$g])) $herkunft[$g][$q] = (int)$n; else $herkunft[$g] += (int)$n;
    }
    $geraete = ['Handy' => 0, 'Computer' => 0, 'Tablet' => 0];
    $s = $db->prepare('SELECT geraet, besucher FROM geraete WHERE tag = ?');
    $s->execute([$tag]);
    foreach ($s->fetchAll(PDO::FETCH_NUM) as [$g, $n]) if (isset($geraete[$g])) $geraete[$g] = (int)$n;
    $s = $db->prepare('SELECT robots FROM tage WHERE tag = ?');
    $s->execute([$tag]);

    return [
        'tag' => $tag, 'erstellt' => date('Y-m-d H:i'), 'beginn' => $beginn, 'verlauf' => $verlauf,
        'monat' => $summe(date('Y-m-01', $ts)), 'jahr' => $summe(date('Y-01-01', $ts)),
        'seiten' => $seiten, 'seiten_anzahl' => count($alle), 'herkunft' => $herkunft, 'geraete' => $geraete,
        'bots' => (int)($s->fetchColumn() ?: 0),
        'newsletter' => bericht_newsletter($tag),
    ];
}

/**
 * Wochenbrief (seit 02.10.2026): Abonnenten und Konten aus der Datenbank des Benutzerbereichs (konto-daten/, nur gelesen) –
 * Stand jetzt, dazu An- und Abmeldungen am Berichtstag und die zuletzt verschickte Ausgabe. null, wenn nicht lesbar.
 */
function bericht_newsletter(string $tag): ?array
{
    $dateien = glob(__DIR__ . '/konto-daten/konto-*.sqlite') ?: [];
    if (!$dateien) return null;
    sort($dateien);
    try {
        $k = new PDO('sqlite:' . $dateien[0], null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_TIMEOUT => 3]);
        if ((int)$k->query('PRAGMA user_version')->fetchColumn() < 6) return null;   // konto.php hat die Newsletter-Felder (Fassung 6) noch nicht angelegt
        $von = strtotime($tag . ' 00:00:00');
        $zahl = $k->prepare('SELECT COUNT(*) FROM newsletter_log WHERE art = ? AND zeit >= ? AND zeit < ?');
        $ereignisse = function (string $art) use ($zahl, $von): int { $zahl->execute([$art, $von, $von + 86400]); return (int)$zahl->fetchColumn(); };
        $letzte = json_decode((string)$k->query("SELECT v FROM meta WHERE k = 'newsletter_letzte'")->fetchColumn(), true);
        return [
            'abonnenten' => (int)$k->query('SELECT COUNT(*) FROM nutzer WHERE newsletter = 1')->fetchColumn(),
            'konten' => (int)$k->query('SELECT COUNT(*) FROM nutzer')->fetchColumn(),
            'an' => $ereignisse('an'), 'ab' => $ereignisse('ab'),
            'letzte' => is_array($letzte) && isset($letzte['kw'], $letzte['empfaenger']) ? $letzte : null,
        ];
    } catch (Throwable $e) {
        error_log('statistik-bericht.php: Newsletter-Zahlen nicht lesbar – ' . $e->getMessage());
        return null;
    }
}

// ---------- Versand ----------

/** Bericht für $tag bauen und verschicken; Tage ohne Zählung werden übersprungen (true). Räumt alte Tageswerte auf.
 *  $test: Testmail über den laufenden Tag – wird auch ohne Zählung verschickt und im Betreff markiert. */
function bericht_senden(PDO $db, string $tag, bool $test = false): bool
{
    $grenze = date('Y-m-d', strtotime('-' . AUFBEWAHREN_MONATE . ' months'));
    foreach (['tage', 'seiten', 'herkunft', 'geraete'] as $t) $db->prepare("DELETE FROM $t WHERE tag < ?")->execute([$grenze]);

    $d = bericht_daten($db, $tag);
    if (!isset($d['verlauf'][$tag]) && !$test) return true;   // an diesem Tag wurde (noch) nicht gezählt
    $pdf = bericht_pdf($d);
    $h = $d['verlauf'][$tag] ?? ['b' => 0, 'a' => 0];
    $vortag = $d['verlauf'][date('Y-m-d', strtotime("$tag -1 day"))] ?? null;
    [$delta] = b_delta($h['b'], $vortag['b'] ?? null);
    $WT = ['Sonntag', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag'];
    $MO = ['', 'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'];
    $ts = strtotime($tag);
    $betreff = ($test ? 'Testmail – ' : '') . 'Bondarium: ' . b_zahl($h['b']) . ' Besucher am ' . b_tag($tag) . ($delta !== '–' && $delta !== 'neu' ? " ($delta zum Vortag)" : '');
    $top = $d['seiten'][0] ?? null;
    $text = ($test ? 'Testmail: Bericht über den laufenden Tag, Stand ' . date('H:i') . " Uhr. Der echte Bericht kommt jeden Morgen ab 6 Uhr für den Vortag.\n\n" : '') .
        'Besucherbericht für ' . $WT[date('w', $ts)] . ', ' . date('j', $ts) . '. ' . $MO[date('n', $ts)] . ' ' . date('Y', $ts) . "\n\n" .
        'Besucher: ' . b_zahl($h['b']) . ($delta !== '–' ? " ($delta zum Vortag)" : '') . "\n" .
        'Seitenaufrufe: ' . b_zahl($h['a']) . "\n" .
        ($top ? 'Meistbesuchte Seite: ' . $top[1] . ' (' . b_zahl($top[2]) . ' Aufrufe)' . "\n" : '') .
        (is_array($d['newsletter']) ? 'Newsletter-Abonnenten: ' . b_zahl($d['newsletter']['abonnenten'])
            . ($d['newsletter']['an'] || $d['newsletter']['ab'] ? ' (' . ($d['newsletter']['an'] ? '+' . $d['newsletter']['an'] : '') . ($d['newsletter']['an'] && $d['newsletter']['ab'] ? ', ' : '') . ($d['newsletter']['ab'] ? '−' . $d['newsletter']['ab'] : '') . ')' : '')
            . ' bei ' . b_zahl($d['newsletter']['konten']) . ($d['newsletter']['konten'] === 1 ? ' Konto' : ' Konten') . "\n" : '') .
        "\nDer ausführliche Bericht hängt als PDF an.\n\n– automatisch erstellt von " . SEITE . "\n";
    $datei = 'Bondarium-Besucherbericht-' . $tag . '.pdf';

    if (LOKAL) {
        return file_put_contents(STAT_DATEN . '/' . $datei, $pdf) !== false
            && file_put_contents(STAT_DATEN . '/lokal-mail.txt', "An: " . BERICHT_AN . "\nBetreff: $betreff\nAnhang: $datei\n\n$text") !== false;
    }
    $grenzeMime = 'b-' . bin2hex(random_bytes(12));
    $kopf = implode("\r\n", [
        'From: Bondarium <' . BERICHT_AN . '>',
        'MIME-Version: 1.0',
        'Content-Type: multipart/mixed; boundary="' . $grenzeMime . '"',
        'Auto-Submitted: auto-generated',
    ]);
    $koerper = "--$grenzeMime\r\nContent-Type: text/plain; charset=UTF-8\r\nContent-Transfer-Encoding: base64\r\n\r\n" .
        chunk_split(base64_encode($text)) .
        "--$grenzeMime\r\nContent-Type: application/pdf; name=\"$datei\"\r\nContent-Transfer-Encoding: base64\r\n" .
        "Content-Disposition: attachment; filename=\"$datei\"\r\n\r\n" . chunk_split(base64_encode($pdf)) . "--$grenzeMime--\r\n";
    return mail(BERICHT_AN, '=?UTF-8?B?' . base64_encode($betreff) . '?=', $koerper, $kopf, '-f ' . BERICHT_AN);
}
