


- go to next page adn get number result, done 

- refactor go to captcha solver, pre processing and post processing (so captcha solver is reusable), done 

- create test for captcha solver (with url directly), done 

- implement concurrency options, done 

- solve captcha without having to go to captcha page : extract captcha prams, provide them to solver and produce token, done 

- solve problem with domain spoofing. hosts file in C:\Windows\System32\drivers\etc includes the dncl domain so the captcha works but the original wbesite can't be accessed anymore. so we need to add it when replcating the captcha and removing it when done. or a simpelr solution by adding a chrome arg dns resolver like in simple_captcha_solver.py (check seleniumabse docs on how to add an arg)


- test with webshare proxy / test with proxy control mobile proxy 

- send request with captcha token instead of going to next page 
- add lnnte usecase 