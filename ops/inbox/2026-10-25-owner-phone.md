# Owner, 2026-10-25: the phone view

Verbatim:

> As for the phone layout, it looks absolutely horrible. It's hard to touch buttons. It runs very
> slowly. I think it's very intensive. I think just put the desktop view on the phone and keep it at
> a fixed landscape. And even if you turn your phone portrait, it stays on the landscape mode. That
> way everything is a lot smoother. Make sure it looks good. You may use a mobile viewer to see what
> it looks like, and make sure it's interactive so that it runs on the processing of a phone.

Also: the Pi installer and the Third Eye hardware run are not asks of the owner any more ("I don't
know why you still want me to do the thing on the Pi"). They are optional verification only, and
nothing is blocked on them.

Done in the phone-stage PR: phones get /phone, a fixed landscape stage holding the 1180 px desktop
composition (turned when upright), lite rendering, touch scrolling in both orientations, touch
forgiveness on small controls. Verified in Chromium phone emulation (iPhone 13, Pixel 7, both
orientations); real Safari and real phones are not verified from the cloud.
