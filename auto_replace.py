#!/usr/bin/env python3

from __future__ import print_function
import time
import json
import re
import sys
import subprocess as sp
from datetime import datetime


def print(s, end='\n', file=sys.stdout):
    file.write(s + end)
    file.flush()


max_fee_cap = 9_000_000_000
max_premium = 8_000_000

def curr_base_fee():
    current_base_fee = sp.getoutput(r"lotus chain getblock `lotus chain head` | grep ParentBaseFee| tail -n 1|awk '{print $2}'| tr -d [,\"]").split()[0]
    base_fee = int(current_base_fee)
    if base_fee < max_fee_cap:
        return int(base_fee*1.10)
    else:
        return max_fee_cap   

def plus_premium(premium):
    if (premium > max_premium):
        return max_premium
    else:
        return int(premium * 1.25)

def loop():
    # vars and definitions
    class MsgInfo(object):
        def __init__(self, t, f, n, c, p):
            self.view_time = t
            self.from_addr = f
            self.nonce = n
            self.fee_cap = c
            self.premium = p

    msg_dict = dict()

    while True:
        fee_cap = curr_base_fee()
        print("base fee: {}".format(fee_cap))

        local_pending_msgs_str = sp.getoutput("lotus mpool pending --local | jq -s '.'")
        local_pending_msgs = json.loads(local_pending_msgs_str)

        if len(local_pending_msgs) == 0:
            msg_dict = dict()
            print("no pending message!")
        else:
            # clear msg_dict
            current_ids = set()
            for m in local_pending_msgs:
                msg_id = m['CID']['/']
                current_ids.add(msg_id)
            for msg_id in list(msg_dict):
                if msg_id not in current_ids:
                    del msg_dict[msg_id]

            # add new msgs to msg_dict
            for m in local_pending_msgs:
                msg_id = m['CID']['/']
                if msg_id not in msg_dict:
                    from_addr = m['Message']['From']
                    nonce = m['Message']['Nonce']
                    fee_cap = m['Message']['GasFeeCap']
                    premium = m['Message']['GasPremium']
                    vt = int(round(time.time()))
                    msg_dict[msg_id] = MsgInfo(vt, from_addr, nonce, fee_cap, premium)

            # dump pending messages
            now = datetime.now()
            ts = now.strftime("%Y/%m/%d-%H:%M:%S")
            # print("dump msg_dict:")
            # for key in msg_dict:
            #     print(ts + ' ' + msg_dict[key].from_addr + ' ' + str(msg_dict[key].nonce) + ' ' + key)

            # deal with blocked msgs
            curr_time = int(round(time.time()))
            index = 0
            for info in msg_dict:
                index += 1
                # diff = curr_time - msg_dict[info].view_time
                # if diff > 40:
                if index <= 10:
                    from_addr = msg_dict[info].from_addr
                    nonce = msg_dict[info].nonce

                    cmd = "lotus mpool replace --gas-feecap " + str(fee_cap) + " --gas-premium 1000" + " " + from_addr + " " + str(nonce)
                    print("\nrunning command:\n" + cmd)
                    out = sp.getoutput(cmd)

                    match = re.match(r'ERROR: failed to push new message to mempool: failed to add locked: message from (.*) with nonce (.*) '
                                     r'already in mpool, increase GasPremium to (.*) from (.*) to trigger replace by '
                                     r'fee: replace by fee has too low GasPremium', out)
                    if match:
                        print("adjusting gas-premium and try again ...")
                        # m_from = match.group(1)
                        # m_nonce = match.group(2)
                        m_gaspremium = match.group(3)
                        gas_premium = plus_premium(int(m_gaspremium))


                        command = "lotus mpool replace --gas-feecap " + str(fee_cap) + " --gas-premium " + \
                                  str(gas_premium) + " " + from_addr + " " + str(nonce)
                        print("running command:\n" + command)
                        out2 = sp.getoutput(command)
                        print(out2)
                    else:
                        print(out)
                else:
                    break        

        # sleep
        print("sleep 180 seconds\n")
        time.sleep(180)


def main():
    loop()


if __name__ == "__main__":
    main()