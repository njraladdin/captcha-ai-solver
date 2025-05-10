


- go to next page adn get number result, done 
- refactor go to captcha solver, pre processing and post processing (so captcha solver is reusable), done 
- create test for captcha solver (with url directly), done 
- implement concurrency options, done 
- solve captcha without having to go to captcha page : extract captcha prams, provide them to solver and produce token, done 
- solve problem with domain spoofing. hosts file in C:\Windows\System32\drivers\etc, add ssl certificate, done 
- fix captcha not being submitted : only do the token inject, check if it was added properly, done 
- test with webshare proxy / test with proxy control mobile proxy (test original captcha and replicated captcha having different proxies), done 
- publish pip package, done 


- add utilities to help extract captcha params from the page and to submit captcha. maybe an utlities sub module? but they are not part of the main logic. those are simpyl helpers / utilities. the main module should be used as params input -> token output.
