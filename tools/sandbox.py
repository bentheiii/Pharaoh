import pafy

pafy_list = pafy.get_playlist2('PLHknatatJlKJnA6HyDB5oH_LhNzzWdN6A')
for paf in pafy_list:
    print(paf)