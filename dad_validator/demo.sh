export SHACS_DEMO_HOME=/home/craig/shacs/shacs

export DADEXEC=$SHACS_DEMO_HOME/dad-poc/dadpoc
export VALIDATOR='python3 /home/craig/shacs/shacs/dad-validator.py'

#IMT Test 1
# Subaru (from DND)
# Denial of Service (Single Attack)
# 200 Messages
# Attack on message 0x152
# Training Data 25,000 Messages (5 minutes)
# Monitoring Data 25,200 Messages
cd /home/craig/shacs/shacs/dad-poc/demo/imt/test001
$DADEXEC -t serdump-2015-11-19_174616_id152_a.log -m serdump-2015-11-19_174616_id152_a.dos_vol.log -i -n deleteme
$VALIDATOR -t serdump-2015-11-19_174616_id152_a -a dos_vol -d test001 -I -T /home/craig/shacs/shacs/dad-poc/dad_validation.html -C 'Subaru DoS Volume Attack 200 Messages'


#IMT Test 2
#  Kia 
#  Denial of Service (Single Vehicle)
#  200 Attack messages
#  Attack on message 0x130
#  Training file 190,236 messages (30 minutes)
#  Montioring file 190,436 messages
cd /home/craig/shacs/shacs/dad-poc/demo/imt/200msgs
$DADEXEC -t ./Attack_free_Kia_Soul_02_id_0130.log -m ./Attack_free_Kia_Soul_02_id_0130.dos_vol.log -i -n deleteme
$VALIDATOR -t Attack_free_Kia_Soul_02_id_0130 -a dos_vol -d test3 -I -T /home/craig/shacs/shacs/dad-poc/dad_validation.html -C 'Kia DoS Volume Attack 200 messages'

#IMT Test 3
#   Kia 
#   Denial of Service (Multiple Attacks)
#   200x2 Messages
#   Attack on message 0x130
#   Training file 190,236 messages (30 minutes)
#   Montioring file 190,436 messages
cd /home/craig/shacs/shacs/dad-poc/demo/imt/200_b
$DADEXEC -t ./Attack_free_Kia_Soul_02_id_0130.log -m ./Attack_free_Kia_Soul_02_id_0130.dos_vol.log -i -n testx
$VALIDATOR -t Attack_free_Kia_Soul_02_id_0130 -a dos_vol -d testx -I -T /home/craig/shacs/shacs/dad-poc/dad_validation.html -C 'Kia DoS Attack (2 x 200 msgs)'



#Entropy Test 1
#   Fuzzy Attack with Message Insertion
#   257 Messages Inserted
#   Attack on message 0x152
#   Training File 29366 Messages
#   Monitoring File 29623 Messages
cd /home/craig/shacs/shacs/dad-poc/demo/fuzzy/ins/257msgs
$DADEXEC -t ./Attack_free_Kia_Soul_02_id_152.log -m ./Attack_free_Kia_Soul_02_id_152.fuzzy_ins.log -e -n deleteme
$VALIDATOR -t Attack_free_Kia_Soul_02_id_152 -a fuzzy_ins -d test100 -H -T /home/craig/shacs/shacs/dad-poc/dad_validation.html -C 'Fuzzy Attack Inserted 257 msgs'

#Entropy Test 2
#    Kia
#    Fuzzy attack (Message Overwrite)
#    2000 total attack messages.
#    Attack on message 0x2C0
#    Training file 190489 Messages
#    Monitoring file 190489 Messages
cd /home/craig/shacs/shacs/dad-poc/demo/fuzzy/owrite/test3_2000
$DADEXEC -t ./Attack_free_Kia_Soul_02_id02c0.log -m ./Attack_free_Kia_Soul_02_id02c0.fuzzy_owrite.log -e -n deleteme
$VALIDATOR -t Attack_free_Kia_Soul_02_id02c0 -a fuzzy_owrite -d deleteme -H -T /home/craig/shacs/shacs/dad-poc/dad_validation.html -C 'Fuzzy Attack Overwrite 2000 msgs'


#Entropy Test 3
cd /home/craig/shacs/shacs/dad-poc/validation/Kia_m304/replay
$DADEXEC -t ../Kia_m304.log -m ./Kia_m304.replay_sm.log -i -e -n test1 -l
$VALIDATOR -t Kia_m304 -a replay_sm -d test1 -H -T /home/craig/shacs/shacs/dad-poc/dad_validation.html -C 'Kia Entropy Replay Insert 50msgs'
