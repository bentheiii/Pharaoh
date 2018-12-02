import argparse

from pharaohlib import Phar, AddSuggestion, RemoveSuggestion, Mode

from pharaohCLI.asker import Asker
from pharaohCLI.__data__ import __version__


def sync(phar: Phar, args: dict):
    phar.fetch()
    print(f'current destination is {phar.destination}')
    rules = {'msg': 'show', 'add': 'ask', 'del': 'ask'}
    if args['rule']:
        for cat, action in args['rule']:
            if cat in ('msg',):
                if action not in ('show', 'hide'):
                    raise Exception('msg actions must be either show or hide')
            elif cat in ('add', 'del'):
                if action not in ('y', 'n', 'ask'):
                    raise Exception('add and del actions must be either y, n, or ask')
            else:
                raise Exception('rule category must be either msg, add, or del')
            rules[cat] = action

    asker = Asker()
    for suggestion in phar.suggest_edits():
        if isinstance(suggestion, str):
            if rules['msg'] == 'show':
                print(suggestion)
        else:
            if isinstance(suggestion, AddSuggestion):
                rule = rules['add']
            elif isinstance(suggestion, RemoveSuggestion):
                rule = rules['del']
            else:
                assert False, 'bad suggestion' + repr(suggestion)
            accept = asker.ask(rule, str(suggestion))
            if accept:
                suggestion.accept()
            else:
                suggestion.reject()


def main(args=None):
    parser = argparse.ArgumentParser('pharaohCLI')
    parser.add_argument('--version', action='version', version=__version__)

    parser = argparse.ArgumentParser(description='A CLI tool for mystic files')
    sub_parsers = parser.add_subparsers()

    create_parser = sub_parsers.add_parser('create')
    create_parser.add_argument('path', action='store')
    create_parser.add_argument('mode', action='store')
    create_parser.add_argument('source', action='store')
    create_parser.add_argument('destinations', action='store', nargs='+')
    create_parser.add_argument('--fetch', action='store_true', dest='fetch', default=False)
    create_parser.set_defaults(create=True)

    open_parser = sub_parsers.add_parser('open')
    open_parser.add_argument('path', action='store')
    open_parser.set_defaults(open=True)
    open_sub_parsers = open_parser.add_subparsers()

    sync_parser = open_sub_parsers.add_parser('sync')
    sync_parser.add_argument('--rule', action='append', nargs=2)
    sync_parser.set_defaults(sync=True)

    set_source_parser = open_sub_parsers.add_parser('set_source')
    set_source_parser.add_argument('source', action='store')
    set_source_parser.set_defaults(set_source=True)

    add_dest_parser = open_sub_parsers.add_parser('add_destinations')
    add_dest_parser.add_argument('paths', nargs='+', action='store')
    add_dest_parser.set_defaults(add_destinations=True)

    set_dest_parser = open_sub_parsers.add_parser('set_destinations')
    set_dest_parser.add_argument('paths', nargs='+', action='store')
    set_dest_parser.set_defaults(set_destinations=True)

    set_mode_parser = open_sub_parsers.add_parser('set_mode')
    set_mode_parser.add_argument('mode')
    set_mode_parser.set_defaults(set_mode=True)

    clean_list_parser = open_sub_parsers.add_parser('clean')
    clean_list_parser.add_argument('--whitelist', '-w', action='store_true', default=False, dest='clean_white')
    clean_list_parser.add_argument('--blacklist', '-b', action='store_true', default=False, dest='clean_black')
    clean_list_parser.set_defaults(clean_list=True)

    update_list_parser = open_sub_parsers.add_parser('update')
    update_list_parser.set_defaults(update=True)

    args = parser.parse_args(args)
    args = args.__dict__

    if args.get('create'):
        phar = Phar()
        phar.destinations = args['destinations']
        phar.source = args['source']
        phar.mode = Mode(args['mode'])
        if args['fetch']:
            phar.fetch()
        phar.write(open(args['path'], mode='x'))
    elif args.get('open'):
        phar = Phar.read(open(args['path'], mode='r'))
        if args.get('sync'):
            sync(phar, args)
        elif args.get('set_source'):
            phar.source = args['source']
        elif args.get('add_destinations'):
            phar.destinations.extend(args['paths'])
        elif args.get('set_destinations'):
            phar.destinations = args['path']
        elif args.get('set_mode'):
            phar.mode = Mode(args['mode'])
        elif args.get('clean'):
            if args['clean_white']:
                phar.whitelist.clear()
            if args['clean_black']:
                phar.blacklist.clear()
        elif args.get('update'):
            pass
        else:
            raise Exception('unhandled args state')
        phar.write(open(args['path'], mode='w'))
    else:
        raise Exception('must specify either create or open, run with -h to see help')
