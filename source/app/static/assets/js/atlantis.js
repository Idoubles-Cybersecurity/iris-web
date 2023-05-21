'use strict';
import $ from 'jquery';

$(function(){
    $('.nav-search .input-group > input').focus(function (a) {
        $(this).parent().addClass('focus');
    }).blur(function (a) {
        $(this).parent().removeClass('focus');
    }), $(function () {
        $('[data-toggle="tooltip"]').tooltip();
    }), $(document).ready(function () {
        $('.btn-refresh-card').on('click', function () {
            var a = $(this).parents('.card');
            a.length && (a.addClass('is-loading'), setTimeout(function () {
                a.removeClass('is-loading');
            }, 3000));
        });
        var a = $('.sidebar .scrollbar');
        a.length > 0 && a.scrollbar();
        var e = $('.main-panel .content-scroll');
        e.length > 0 && e.scrollbar();
        var s = $('.messages-scroll');
        s.length > 0 && s.scrollbar();
        var o = $('.tasks-scroll');
        o.length > 0 && o.scrollbar();
        var i = $('.quick-scroll');
        i.length > 0 && i.scrollbar();
        var n = $('.message-notif-scroll');
        n.length > 0 && n.scrollbar();
        var r = $('.notif-scroll');
        r.length > 0 && r.scrollbar();
        var l = $('.quick-actions-scroll');
        l.length > 0 && l.scrollbar();
        var t = $('.dropdown-user-scroll');
        t.length > 0 && t.scrollbar(), $('.scroll-bar').draggable(), $('#search-nav').on('shown.bs.collapse', function () {
            $('.nav-search .form-control').focus();
        });

        var c = !1, d = !1, g = !1, p = !1, h = 0, m = 0, u = 0, f = 0, b = 0;
        if (!c) {
            (C = $('.sidenav-toggler')).on('click', function () {
                1 == h ? ($('html').removeClass('nav_open'), C.removeClass('toggled'), h = 0) : ($('html').addClass('nav_open'), C.addClass('toggled'), h = 1);
            }), c = !0;
        }
        if (!m) {
            var C = $('.quick-sidebar-toggler');
            C.on('click', function () {
                1 == h ? ($('html').removeClass('quick_sidebar_open'), $('.quick-sidebar-overlay').remove(), C.removeClass('toggled'), m = 0) : ($('html').addClass('quick_sidebar_open'), C.addClass('toggled'), m = 1);
            }), $('.wrapper').mouseup(function (a) {
                var e = $('.quick-sidebar');
                a.target.className == e.attr('class') || e.has(a.target).length || ($('html').removeClass('quick_sidebar_open'), $('.quick-sidebar-toggler').removeClass('toggled'), $('.quick-sidebar-overlay').remove(), m = 0);
            }), $('.close-quick-sidebar').on('click', function () {
                $('html').removeClass('quick_sidebar_open'), $('.quick-sidebar-toggler').removeClass('toggled'), $('.quick-sidebar-overlay').remove(), m = 0;
            }), m = !0;
        }
        if (!d) {
            var w = $('.topbar-toggler');
            w.on('click', function () {
                1 == u ? ($('html').removeClass('topbar_open'), w.removeClass('toggled'), u = 0) : ($('html').addClass('topbar_open'), w.addClass('toggled'), u = 1);
            }), d = !0;
        }
        if (!p) {
            var _ = $('.page-sidebar-toggler');
            _.on('click', function () {
                1 == f ? ($('html').removeClass('pagesidebar_open'), _.removeClass('toggled'), f = 0) : ($('html').addClass('pagesidebar_open'), _.addClass('toggled'), f = 1);
            });
            $('.page-sidebar .back').on('click', function () {
                $('html').removeClass('pagesidebar_open'), _.removeClass('toggled'), f = 0;
            }), p = !0;
        }
        var y = $('.sidenav-overlay-toggler');
        $('.wrapper').hasClass('is-show') && (b = 1, y.addClass('toggled'), y.html('<i class="icon-options-vertical"></i>')), y.on('click', function () {
            1 == b ? ($('.wrapper').removeClass('is-show'), y.removeClass('toggled'), y.html('<i class="icon-menu"></i>'), b = 0) : ($('.wrapper').addClass('is-show'), y.addClass('toggled'), y.html('<i class="icon-options-vertical"></i>'), b = 1), $(window).resize();
        }), g = !0, $('.sidebar').hover(function () {
            $('.wrapper').hasClass('sidebar_minimize') && $('.wrapper').addClass('sidebar_minimize_hover');
        }, function () {
            $('.wrapper').hasClass('sidebar_minimize') && $('.wrapper').removeClass('sidebar_minimize_hover');
        }), $('.nav-item a').on('click', function () {
            $(this).parent().find('.collapse').hasClass('show') ? $(this).parent().removeClass('submenu') : $(this).parent().addClass('submenu');
        }), $('.messages-contact .user a').on('click', function () {
            $('.tab-chat').addClass('show-chat');
        }), $('.messages-wrapper .return').on('click', function () {
            $('.tab-chat').removeClass('show-chat');
        }), $('[data-select="checkbox"]').change(function () {
            var a = $(this).attr('data-target');
            $(a).prop('checked', $(this).prop('checked'));
        }), $('.form-group-default .form-control').focus(function () {
            $(this).parent().addClass('active');
        }).blur(function () {
            $(this).parent().removeClass('active');
        });
    });
});