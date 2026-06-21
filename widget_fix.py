content = open('templates/index.html', 'r', encoding='utf-8').read()

widget = """
<div id="chat-btn" onclick="toggleChat()" style="position:fixed;bottom:28px;right:28px;z-index:9999;background:#6c3fc5;color:#fff;border-radius:50%;width:58px;height:58px;display:flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:0 4px 24px rgba(108,63,197,0.4);font-size:26px;">&#128172;</div>
<div id="chat-modal" style="display:none;position:fixed;bottom:100px;right:28px;z-index:9998;width:340px;max-width:95vw;background:#1a0a2e;border-radius:18px;box-shadow:0 8px 40px rgba(108,63,197,0.35);overflow:hidden;flex-direction:column;">
  <div style="background:#6c3fc5;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;">
    <span style="color:#fff;font-weight:600;">veraxIA</span>
    <button onclick="toggleChat()" style="background:none;border:none;color:#fff;font-size:20px;cursor:pointer;">x</button>
  </div>
  <div id="chatMsgs" style="padding:16px;height:300px;overflow-y:auto;display:flex;flex-direction:column;gap:10px;"></div>
  <div style="padding:12px;border-top:1px solid #2d1a4e;display:flex;gap:8px;">
    <input id="chatInput" type="text" placeholder="Escribe tu mensaje..." style="flex:1;background:#2d1a4e;border:none;border-radius:10px;padding:10px 14px;color:#fff;font-size:14px;outline:none;" onkeydown="if(event.key==='Enter')sendMsg()"/>
    <button onclick="sendMsg()" style="background:#6c3fc5;border:none;border-radius:10px;padding:10px 14px;color:#fff;cursor:pointer;">&#10148;</button>
  </div>
</div>
<script>
var chatOpen=false;
var conversationHistory=[];
var chatMsgs=document.getElementById('chatMsgs');
function toggleChat(){chatOpen=!chatOpen;document.getElementById('chat-modal').style.display=chatOpen?'flex':'none';if(chatOpen&&chatMsgs.children.length===0)addMsg('Hola, soy veraxIA. En que puedo ayudarte hoy?',false);}
function addMsg(text,isUser){var d=document.createElement('div');d.style.cssText=isUser?'align-self:flex-end;background:#6c3fc5;color:#fff;padding:8px 14px;border-radius:14px;max-width:80%;font-size:14px;':'align-self:flex-start;background:#2d1a4e;color:#e8d5ff;padding:8px 14px;border-radius:14px;max-width:80%;font-size:14px;';d.textContent=text;chatMsgs.appendChild(d);chatMsgs.scrollTop=chatMsgs.scrollHeight;}
async function sendMsg(){var input=document.getElementById('chatInput');var text=input.value.trim();if(!text)return;input.value='';addMsg(text,true);conversationHistory.push({role:'user',content:text});var t=document.createElement('div');t.id='typing';t.style.cssText='align-self:flex-start;background:#2d1a4e;color:#e8d5ff;padding:8px 14px;border-radius:14px;font-size:14px;';t.textContent='...';chatMsgs.appendChild(t);chatMsgs.scrollTop=chatMsgs.scrollHeight;try{var r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,history:conversationHistory})});var data=await r.json();var el=document.getElementById('typing');if(el)el.remove();var reply=data.response||data.reply||data.message||'Sin respuesta';addMsg(reply,false);conversationHistory.push({role:'assistant',content:reply});}catch(e){var el=document.getElementById('typing');if(el)el.remove();addMsg('Error conectando. Intenta de nuevo.',false);}}
</script>
</body>"""

content = content.replace('</body>', widget)
open('templates/index.html', 'w', encoding='utf-8').write(content)
print('OK - Widget agregado!')