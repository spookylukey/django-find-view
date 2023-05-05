#!/usr/bin/env python3
import argparse
import sys
import os
import inspect


try:
    from dotenv import load_dotenv, find_dotenv

    load_dotenv(dotenv_path=find_dotenv(usecwd=True))
except ImportError:
    pass

if not "DJANGO_SETTINGS_MODULE" in os.environ:
    raise AssertionError("You need DJANGO_SETTINGS_MODULE in your os.environ")

if "DJANGO_CONFIGURATION" in os.environ:
    try:
        import configurations
    except ImportError:
        pass
    else:
        configurations.setup()


import django

django.setup()


from django.urls.exceptions import NoReverseMatch
from django.urls.resolvers import URLPattern, get_resolver
from django.urls.base import get_urlconf, get_ns_resolver


def find_named_view(viewname, urlconf=None, args=None, kwargs=None, current_app=None):
    if urlconf is None:
        urlconf = get_urlconf()
    resolver = get_resolver(urlconf)
    args = args or []
    kwargs = kwargs or {}

    if not isinstance(viewname, str):
        view = viewname
    else:
        *path, view = viewname.split(":")

        if current_app:
            current_path = current_app.split(":")
            current_path.reverse()
        else:
            current_path = None

        resolved_path = []
        ns_pattern = ""
        ns_converters = {}
        for ns in path:
            current_ns = current_path.pop() if current_path else None
            # Lookup the name to see if it could be an app identifier.
            try:
                app_list = resolver.app_dict[ns]
                # Yes! Path part matches an app in the current Resolver.
                if current_ns and current_ns in app_list:
                    # If we are reversing for a particular app, use that
                    # namespace.
                    ns = current_ns
                elif ns not in app_list:
                    # The name isn't shared by one of the instances (i.e.,
                    # the default) so pick the first instance as the default.
                    ns = app_list[0]
            except KeyError:
                pass

            if ns != current_ns:
                current_path = None

            try:
                extra, resolver = resolver.namespace_dict[ns]
                resolved_path.append(ns)
                ns_pattern = ns_pattern + extra
                ns_converters.update(resolver.pattern.converters)
            except KeyError as key:
                if resolved_path:
                    raise NoReverseMatch(
                        "%s is not a registered namespace inside '%s'" % (key, ":".join(resolved_path))
                    )
                else:
                    raise NoReverseMatch("%s is not a registered namespace" % key)
        if ns_pattern:
            resolver = get_ns_resolver(ns_pattern, resolver, tuple(ns_converters.items()))

    return find_named_view_from_resolver(resolver, view)


def find_named_view_from_resolver(resolver, view_name) -> URLPattern | None:
    if not resolver._populated:
        resolver._populate()

    for pattern in resolver.url_patterns:
        if hasattr(pattern, "name") and pattern.name == view_name:
            return pattern
        if hasattr(pattern, "url_patterns"):
            result = find_named_view_from_resolver(pattern, view_name)
            if result:
                return result
    return None


def get_function_location(func):
    """Returns the path and line number of a function."""
    if hasattr(func, "__wrapped__"):
        return get_function_location(func.__wrapped__)
    file_path = inspect.getfile(func)
    line_num = inspect.getsourcelines(func)[1]

    return f"{file_path}:{line_num}"


arg_parser = argparse.ArgumentParser(
    description="For a given Django view name, return filename:linenum where it is implemented."
)
arg_parser.add_argument("view_name")


def main():
    args = arg_parser.parse_args()
    view_name = args.view_name
    pattern = find_named_view(view_name)
    if pattern is None:
        print(f"Could not find view called '{view_name}'", file=sys.stderr)
        sys.exit(1)
    print(get_function_location(pattern.callback))
