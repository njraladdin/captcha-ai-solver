


- go to next page adn get number result, done 
- refactor go to captcha solver, pre processing and post processing (so captcha solver is reusable), done 
- create test for captcha solver (with url directly), done 
- implement concurrency options, done 
- solve captcha without having to go to captcha page : extract captcha prams, provide them to solver and produce token, done 
- solve problem with domain spoofing. hosts file in C:\Windows\System32\drivers\etc, add ssl certificate, done 
- fix captcha not being submitted : only do the token inject, check if it was added properly, done 
- test with webshare proxy / test with proxy control mobile proxy (test original captcha and replicated captcha having different proxies), done 



- project scope : send captcha prams, get token. set up server to be used by other projects. 
create a script to use it : https://gist.github.com/2captcha/2ee70fa1130e756e1693a5d4be4d8c70
this project is about solving captchas in a server, to be used using any progrmamaing language / lirbary similar to 2captcha api. 
extracting params and submitting solution is already solved in other projects. (simple javascript code injection)
readme contains instructions to setup server. 

meaning this captcha solver starts a server 
it receives request with captcha params, returns with id
it receives request with task id to check captcha solving status
if still processing : 202. if finished : returns solution token. 

- add lnnte usecase 