/// <reference types="../CTAutocomplete" />
import Dungeons from '../Atomx/skyblock/Dungeons'
const ServerSocket = Java.type("java.net.ServerSocket");
const PrintWriter = Java.type("java.io.PrintWriter");

function startServer(text){
    server = new ServerSocket(8080);
    new Thread(() => {
        try {
            const client = server.accept();
            const writer = new PrintWriter(client.getOutputStream(), true);
            writer.println(text)
            writer.close()
            client.close()
            server.close()
        } catch (e) {
            ChatLib.chat(e);
        }
    }).start();
}



const ProcessBuilder = Java.type("java.lang.ProcessBuilder");
const File = Java.type("java.io.File");
register('command', () => {
    const roomName = Dungeons.getCurrentRoomName()
    if(roomName === undefined) return ChatLib.chat('Error getting the room you are in')
    let text = roomName.toLowerCase()
    //few rooms that arent named right
    if(text == 'dino site') text = 'dino dig site'
    if(text == 'black flag') text = 'black flags'
    const inventory = Player.getInventory()
    inventory.getItems().forEach(item => {
        if(item !== null){
            itemname = item.getName().removeFormatting().toLowerCase()
            if(itemname == 'ender pearl') text += '\nender_pearl'
            else if(itemname == 'tactical insertion') text += '\ntactical_insertion'
        } 
    })
    startServer(text)
    const batchFilePath = (new File('').getAbsolutePath().toString()) + '\\config\\ChatTriggers\\modules\\routes\\index.exe'
    try {
        let processBuilder = new ProcessBuilder(batchFilePath);
        processBuilder.redirectErrorStream(true);
        processBuilder.start();
    } catch (e) {
        console.error(e)
    }
}).setName("route");